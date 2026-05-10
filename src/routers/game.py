import math
import random

from fastapi import APIRouter, HTTPException

from clock import clock
from connections import broadcast
from ecology import flow_rivers
from simulation import MATURITY_AGE
from world import world

router = APIRouter()

NUM_FOOD_CLUSTERS = 3
CLUSTER_SIGMA = 5.0
FOOD_PEAK_PROBABILITY = 0.5
AGENT_COUNT = 20
NUM_SPRINGS = 2


def _food_probability(x: int, y: int, centers: list[tuple[int, int]]) -> float:
    nearest_d2 = min((x - cx) ** 2 + (y - cy) ** 2 for cx, cy in centers)
    return FOOD_PEAK_PROBABILITY * math.exp(-nearest_d2 / (2 * CLUSTER_SIGMA ** 2))


@router.post("/start", status_code=204)
async def start_game() -> None:
    if clock.state != "stopped":
        raise HTTPException(status_code=400, detail="Game is already running")

    all_cells = [(x, y) for x in range(world.width) for y in range(world.height)]

    # Rivers must exist before food placement so clusters form near water
    spring_xs = random.sample(range(world.width), NUM_SPRINGS)
    for x in spring_xs:
        world.add_spring(x, 0)
    while not all(r.complete for r in world.all_rivers()):
        flow_rivers(world, [])

    river_tiles = list(world._river_tiles)
    centers = random.sample(river_tiles, min(NUM_FOOD_CLUSTERS, len(river_tiles)))

    food_placed = []
    for x, y in all_cells:
        if world.is_river_tile(x, y):
            continue
        if random.random() < _food_probability(x, y, centers):
            food = world.place_food(x, y)
            food_placed.append(food.model_dump(mode="json"))

    agents_born = []
    for x, y in random.sample(all_cells, AGENT_COUNT):
        agent = world.add_agent(x, y, age=MATURITY_AGE)
        agents_born.append(agent.model_dump(mode="json"))

    rivers_formed = [
        {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
        for r in world.all_rivers()
    ]

    await broadcast("game_started", {"agents": agents_born, "food": food_placed, "rivers": rivers_formed})
    clock.start()
