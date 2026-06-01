import json
import math
import random
from pathlib import Path

import config as cfg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import deps
from clock import clock
from connections import broadcast
from agents.mutations import seed_genotype
from pos import Pos

router = APIRouter()

WORLDS_DIR = Path(__file__).parent.parent.parent / "worlds"


class StartConfig(BaseModel):
    world_id: str | None = None
    agent_count: int | None = None
    num_springs: int | None = None
    num_food_clusters: int | None = None
    food_peak_probability: float | None = None
    max_age: int | None = None
    hunger_base_drain: float | None = None
    reproduction_chance: float | None = None
    spontaneous_mutation_rate: float | None = None


def _food_probability(pos: Pos, centers: list[Pos]) -> float:
    nearest_d2 = min((pos.x - c.x) ** 2 + (pos.y - c.y) ** 2 for c in centers)
    return cfg.FOOD_PEAK_PROBABILITY * math.exp(
        -nearest_d2 / (2 * cfg.CLUSTER_SIGMA**2)
    )


@router.get("/config")
def get_config() -> dict:
    return {
        "agent_count": cfg.AGENT_COUNT,
        "num_springs": cfg.NUM_SPRINGS,
        "num_food_clusters": cfg.NUM_FOOD_CLUSTERS,
        "food_peak_probability": cfg.FOOD_PEAK_PROBABILITY,
        "max_age": cfg.MAX_AGE,
        "hunger_base_drain": cfg.HUNGER_BASE_DRAIN,
        "reproduction_chance": cfg.REPRODUCTION_CHANCE,
        "spontaneous_mutation_rate": cfg.SPONTANEOUS_MUTATION_RATE,
    }


@router.post("/start", status_code=204)
async def start_game(body: StartConfig = StartConfig()) -> None:
    if clock.state != "stopped":
        raise HTTPException(status_code=400, detail="Game is already running")

    elevation_coarse_scale = 90.0

    if body.world_id is not None:
        path = WORLDS_DIR / f"{body.world_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Saved world not found")
        saved = json.loads(path.read_text())
        seed = saved["seed"]
        saved_config = saved.get("config", {})
        body.num_springs = saved_config.get("num_springs", body.num_springs)
        body.num_food_clusters = saved_config.get(
            "num_food_clusters", body.num_food_clusters
        )
        body.food_peak_probability = saved_config.get(
            "food_peak_probability", body.food_peak_probability
        )
        elevation_coarse_scale = saved_config.get(
            "elevation_coarse_scale", elevation_coarse_scale
        )
    else:
        seed = random.randint(0, 999999)

    cfg.apply_runtime(
        AGENT_COUNT=body.agent_count,
        NUM_SPRINGS=body.num_springs,
        NUM_FOOD_CLUSTERS=body.num_food_clusters,
        FOOD_PEAK_PROBABILITY=body.food_peak_probability,
        MAX_AGE=body.max_age,
        HUNGER_BASE_DRAIN=body.hunger_base_drain,
        REPRODUCTION_CHANCE=body.reproduction_chance,
        SPONTANEOUS_MUTATION_RATE=body.spontaneous_mutation_rate,
    )
    deps.simulation.reset()

    all_cells = [
        Pos(x, y) for x in range(deps.world.width) for y in range(deps.world.height)
    ]

    deps.world.generate_elevation(seed=seed, coarse_scale=elevation_coarse_scale)
    deps.world.weather.generate(seed, lambda x, y: deps.world.elevation_at(Pos(x, y)))

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    peaks = [
        Pos(x, y)
        for x in range(1, deps.world.width - 1)
        for y in range(1, deps.world.height - 1)
        if all(
            deps.world.elevation_at(Pos(x, y))
            > deps.world.elevation_at(Pos(x + dx, y + dy))
            for dx, dy in neighbors
        )
    ]
    if len(peaks) < cfg.NUM_SPRINGS:
        peaks = sorted(
            [
                Pos(x, y)
                for x in range(deps.world.width)
                for y in range(deps.world.height)
            ],
            key=lambda p: deps.world.elevation_at(p),
            reverse=True,
        )
    chosen_springs = random.sample(peaks, min(cfg.NUM_SPRINGS, len(peaks)))
    for pos in chosen_springs:
        deps.world.rivers.add_spring(pos)
    while not all(r.complete for r in deps.world.rivers.all_rivers):
        deps.world.flow_rivers([])

    river_tiles = list(deps.world.rivers.all_tiles)
    centers = random.sample(river_tiles, min(cfg.NUM_FOOD_CLUSTERS, len(river_tiles)))

    food_placed = []
    for pos in all_cells:
        if deps.world.rivers.is_river_tile(pos):
            continue
        if random.random() < _food_probability(pos, centers):
            food = deps.food.place_food(pos)
            food_placed.append(food.model_dump(mode="json"))

    food_positions = [Pos(f["x"], f["y"]) for f in food_placed]
    deps.world.generate_rest_quality(food_positions, seed=random.randint(0, 999999))

    agents_born = []
    for pos in random.sample(all_cells, cfg.AGENT_COUNT):
        agent = deps.agents.add(pos, age=cfg.MATURITY_AGE)
        seed_genotype(agent)
        agents_born.append(agent.model_dump(mode="json"))

    rivers_formed = [
        {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
        for r in deps.world.rivers.all_rivers
    ]

    await broadcast(
        "game_started",
        {
            "agents": agents_born,
            "food": food_placed,
            "rivers": rivers_formed,
            "elevation": deps.world.all_elevation(),
            "temperature": deps.world.weather.base_temperature(),
            "precipitation": deps.world.weather.base_precipitation(),
            "clouds": deps.world.weather.clouds_to_list(),
        },
    )
    clock.start()
