import random

from agents.agent import Agent
from config import (
    FOOD_BASE_WEIGHT,
    FOOD_HUNGER_BONUS,
    FOOD_MEMORY_WEIGHT,
    WANDER_WEIGHT,
)
from plant import Plant
from pos import Pos


def score_move(
    agent: Agent,
    pos: Pos,
    food_targets: list[Plant],
) -> float:
    score = WANDER_WEIGHT * random.random()

    if food_targets:
        nearest_dist = min(abs(f.x - pos.x) + abs(f.y - pos.y) for f in food_targets)
        hunger = 1.0 - agent.needs.hunger
        score += (FOOD_BASE_WEIGHT + FOOD_HUNGER_BONUS * hunger) / (1 + nearest_dist)

    if not food_targets and agent.last_food_seen:
        dist = abs(pos.x - agent.last_food_seen.x) + abs(pos.y - agent.last_food_seen.y)
        score += FOOD_MEMORY_WEIGHT / (1 + dist)

    return score


def best_move(
    agent: Agent,
    candidates: list[Pos],
    food_targets: list[Plant],
) -> Pos:
    best_pos = candidates[0]
    best_score = float("-inf")

    for p in candidates:
        score = score_move(agent, p, food_targets)
        if score > best_score:
            best_score = score
            best_pos = p

    return best_pos
