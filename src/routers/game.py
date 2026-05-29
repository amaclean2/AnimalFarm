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
    adult_drain: int | None = None
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
        "adult_drain": cfg.ADULT_DRAIN,
        "reproduction_chance": cfg.REPRODUCTION_CHANCE,
        "spontaneous_mutation_rate": cfg.SPONTANEOUS_MUTATION_RATE,
        "max_hunger": cfg.MAX_HUNGER,
        "max_rest": cfg.MAX_REST,
        "max_water": cfg.MAX_WATER,
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
        ADULT_DRAIN=body.adult_drain,
        REPRODUCTION_CHANCE=body.reproduction_chance,
        SPONTANEOUS_MUTATION_RATE=body.spontaneous_mutation_rate,
    )
    simulation.reset()

    all_cells = [(x, y) for x in range(world.width) for y in range(world.height)]

    spring_xs = random.sample(range(world.width), cfg.NUM_SPRINGS)
    for x in spring_xs:
        world.add_spring(x, 0)
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
        {"agents": agents_born, "food": food_placed, "rivers": rivers_formed},
    )
    clock.start()
