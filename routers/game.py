import json
import random
from pathlib import Path

import config as cfg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import deps
from clock import clock
from connections import broadcast
from genome import apply_to_agent, mutate, random_genome
from pos import Pos

router = APIRouter()

WORLDS_DIR = Path(__file__).parent.parent.parent / "worlds"


class StartConfig(BaseModel):
    world_id: str | None = None
    agent_count: int | None = None
    num_springs: int | None = None
    max_age: int | None = None
    hunger_base_drain: float | None = None
    reproduction_chance: float | None = None
    spontaneous_mutation_rate: float | None = None


@router.get("/config")
def get_config() -> dict:
    return {
        "agent_count": cfg.AGENT_COUNT,
        "num_springs": cfg.NUM_SPRINGS,
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
        elevation_coarse_scale = saved_config.get(
            "elevation_coarse_scale", elevation_coarse_scale
        )
    else:
        seed = random.randint(0, 999999)

    cfg.apply_runtime(
        AGENT_COUNT=body.agent_count,
        NUM_SPRINGS=body.num_springs,
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
        deps.world.flow_rivers()

    deps.world.generate_river_proximity()

    plants_placed = deps.vegetation.place_plants(seed)
    plant_positions = [Pos(p.x, p.y) for p in plants_placed]
    deps.world.generate_rest_quality(plant_positions, seed=random.randint(0, 999999))

    pool = deps.genome_pool
    use_elite = pool.size() >= cfg.POOL_SEED_THRESHOLD
    elite_genomes = pool.sample_elite(cfg.AGENT_COUNT) if use_elite else []

    agents_born = []
    for i, pos in enumerate(random.sample(all_cells, cfg.AGENT_COUNT)):
        agent = deps.agents.add(pos, age=cfg.MATURITY_AGE)
        genome = (
            mutate(elite_genomes[i], cfg.SPONTANEOUS_MUTATION_RATE)
            if use_elite
            else random_genome()
        )
        agent.behavioral_genome = genome
        apply_to_agent(agent, genome)
        agents_born.append(agent.model_dump(mode="json"))

    rivers_formed = [
        {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
        for r in deps.world.rivers.all_rivers
    ]

    await broadcast(
        "game_started",
        {
            "agents": agents_born,
            "plants": [p.model_dump(mode="json") for p in plants_placed],
            "rivers": rivers_formed,
            "elevation": deps.world.all_elevation(),
            "temperature": deps.world.weather.base_temperature(),
            "precipitation": deps.world.weather.base_precipitation(),
            "clouds": deps.world.weather.clouds_to_list(),
        },
    )
    clock.start()
