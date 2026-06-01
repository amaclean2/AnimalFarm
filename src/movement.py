import random

from agents import Agents
from agents.agent import Agent
from config import (
    VISION_BONUS,
    FOOD_BASE_WEIGHT,
    FOOD_HUNGER_BONUS,
    FOOD_MEMORY_WEIGHT,
    SOCIAL_COHESION_WEIGHT,
    SOCIAL_FRINGE_WEIGHT,
    SOCIAL_LONE_WEIGHT,
    WANDER_WEIGHT,
    MOMENTUM_WEIGHT,
)
from pos import Pos
from food import FoodItem
from group import Group


def effective_vision(agents: Agents, agent: Agent) -> float:
    group = agents.group_for_agent(agent.id)
    if group:
        dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
        if dist <= group.cohesion_radius:
            return agent.vision_range * VISION_BONUS
    return float(agent.vision_range)


def score_move(
    agent: Agent,
    pos: Pos,
    food_targets: list[FoodItem],
    group: Group | None,
    social_target: tuple[float, float, float] | None,
    from_pos: Pos | None = None,
) -> float:
    origin = from_pos if from_pos is not None else agent.pos
    score = WANDER_WEIGHT * random.random()

    if food_targets:
        nearest_dist = min(abs(f.x - pos.x) + abs(f.y - pos.y) for f in food_targets)
        hunger = 1.0 - agent.hunger
        score += (FOOD_BASE_WEIGHT + FOOD_HUNGER_BONUS * hunger) / (1 + nearest_dist)

    if group:
        dist = abs(pos.x - group.center_x) + abs(pos.y - group.center_y)
        weight = (
            SOCIAL_FRINGE_WEIGHT
            if dist > group.cohesion_radius
            else SOCIAL_COHESION_WEIGHT
        )
        if not food_targets:
            hunger = 1.0 - agent.hunger
            weight *= max(0.0, 1.0 - hunger)
        score += weight / (1 + dist)
    elif social_target:
        tx, ty, gravity = social_target
        dist = abs(pos.x - tx) + abs(pos.y - ty)
        score += SOCIAL_LONE_WEIGHT * gravity / (1 + dist)

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
    food_targets: list[FoodItem],
    group: Group | None,
    social_target: tuple[float, float, float] | None,
) -> Pos:
    best_pos = candidates[0]
    best_score = float("-inf")
    for p in candidates:
        score = score_move(agent, p, food_targets, group, social_target)
        if score > best_score:
            best_score = score
            best_pos = p
    return best_pos


def lone_social_target(
    agents: Agents, agent: Agent, vision: float
) -> tuple[float, float, float] | None:
    best: tuple[float, float, float] | None = None
    best_score = 0.0

    for group in agents.all_groups:
        dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
        if dist <= vision:
            score = group.gravity / (1 + dist)
            if score > best_score:
                best_score = score
                best = (group.center_x, group.center_y, group.gravity)

    for other in agents.in_range(agent, vision):
        if other.group_id is None:
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            score = 1.0 / (1 + dist)
            if score > best_score:
                best_score = score
                best = (float(other.x), float(other.y), 1.0)

    return best
