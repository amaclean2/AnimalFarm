import random

from agents.agent import Agent
from config import (
    FOOD_BASE_WEIGHT,
    FOOD_HUNGER_BONUS,
    FOOD_MEMORY_WEIGHT,
    WANDER_WEIGHT,
    MOMENTUM_WEIGHT,
)
from plant import Plant
from pos import Pos


def score_move(
    agent: Agent,
    pos: Pos,
    food_targets: list[Plant],
    from_pos: Pos | None = None,
) -> float:
    origin = from_pos if from_pos is not None else agent.pos
    score = WANDER_WEIGHT * random.random()

    if food_targets:
        nearest_dist = min(abs(f.x - pos.x) + abs(f.y - pos.y) for f in food_targets)
        hunger = 1.0 - agent.hunger
        score += (FOOD_BASE_WEIGHT + FOOD_HUNGER_BONUS * hunger) / (1 + nearest_dist)

    if agent.direction:
        dx, dy = pos.x - origin.x, pos.y - origin.y
        dot = agent.direction[0] * dx + agent.direction[1] * dy
        lost = not food_targets and not agent.last_food_seen
        satiation = 1.0 if lost else agent.hunger**2
        score += MOMENTUM_WEIGHT * max(0.0, dot) * satiation

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
