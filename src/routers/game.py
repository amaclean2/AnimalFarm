import math
import random

import config as cfg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clock import clock
from connections import broadcast
from ecology import flow_rivers
from agent.mutations import seed_genotype
from simulation import simulation
from world import world

router = APIRouter()


class StartConfig(BaseModel):
    agent_count: int | None = None
    num_springs: int | None = None
    num_food_clusters: int | None = None
    food_peak_probability: float | None = None
    max_age: int | None = None
    hunger_base_drain: float | None = None
    reproduction_chance: float | None = None
    spontaneous_mutation_rate: float | None = None


def _food_probability(x: int, y: int, centers: list[tuple[int, int]]) -> float:
    nearest_d2 = min((x - cx) ** 2 + (y - cy) ** 2 for cx, cy in centers)
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
    simulation.reset()

    all_cells = [(x, y) for x in range(world.width) for y in range(world.height)]

    seed = random.randint(0, 999999)
    world.generate_elevation(seed=seed)
    world.generate_climate(seed=seed)

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    peaks = [
        (x, y)
        for x in range(1, world.width - 1)
        for y in range(1, world.height - 1)
        if all(
            world.elevation_at(x, y) > world.elevation_at(x + dx, y + dy)
            for dx, dy in neighbors
        )
    ]
    if len(peaks) < cfg.NUM_SPRINGS:
        peaks = sorted(
            [(x, y) for x in range(world.width) for y in range(world.height)],
            key=lambda p: world.elevation_at(*p),
            reverse=True,
        )
    chosen_springs = random.sample(peaks, min(cfg.NUM_SPRINGS, len(peaks)))
    for x, y in chosen_springs:
        world.add_spring(x, y)
    while not all(r.complete for r in world.all_rivers()):
        flow_rivers(world, [])

    river_tiles = list(world._river_tiles)
    centers = random.sample(river_tiles, min(cfg.NUM_FOOD_CLUSTERS, len(river_tiles)))

    food_placed = []
    for x, y in all_cells:
        if world.is_river_tile(x, y):
            continue
        if random.random() < _food_probability(x, y, centers):
            food = world.place_food(x, y)
            food_placed.append(food.model_dump(mode="json"))

    food_positions = [(f["x"], f["y"]) for f in food_placed]
    world.generate_rest_quality(food_positions, seed=random.randint(0, 999999))

    agents_born = []
    for x, y in random.sample(all_cells, cfg.AGENT_COUNT):
        agent = world.add_agent(x, y, age=cfg.MATURITY_AGE)
        seed_genotype(agent)
        agents_born.append(agent.model_dump(mode="json"))

    rivers_formed = [
        {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
        for r in world.all_rivers()
    ]

    await broadcast(
        "game_started",
        {
            "agents": agents_born,
            "food": food_placed,
            "rivers": rivers_formed,
            "elevation": world.all_elevation(),
            "temperature": world.all_temperature(),
            "precipitation": world.all_precipitation(),
            "clouds": world.clouds_to_list(),
        },
    )
    clock.start()
