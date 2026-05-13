import random

from agent import MAX_HEALTH, Agent
from food import Food
from group import Group, VISION_BONUS
from world import World

FOOD_BASE_WEIGHT = 4.0
FOOD_HUNGER_BONUS = 4.0
FOOD_MEMORY_WEIGHT = 1.5
SOCIAL_COHESION_WEIGHT = 2.0
SOCIAL_FRINGE_WEIGHT = 4.0
SOCIAL_LONE_WEIGHT = 1.5
WANDER_WEIGHT = 0.15
MOMENTUM_WEIGHT = 0.3
LOOKAHEAD_DISCOUNT = 0.5


def effective_vision(world: World, agent: Agent) -> float:
    group = world.group_for_agent(agent.id)
    if group:
        dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
        if dist <= group.cohesion_radius:
            return agent.vision_range * VISION_BONUS
    return float(agent.vision_range)


def score_move(
    agent: Agent,
    pos: tuple[int, int],
    food_targets: list[Food],
    group: Group | None,
    social_target: tuple[float, float, float] | None,
    from_pos: tuple[int, int] | None = None,
) -> float:
    origin = from_pos if from_pos is not None else (agent.x, agent.y)
    score = WANDER_WEIGHT * random.random()

    if food_targets:
        nearest_dist = min(abs(f.x - pos[0]) + abs(f.y - pos[1]) for f in food_targets)
        hunger = (MAX_HEALTH - agent.health) / MAX_HEALTH
        score += (FOOD_BASE_WEIGHT + FOOD_HUNGER_BONUS * hunger) / (1 + nearest_dist)

    if group:
        dist = abs(pos[0] - group.center_x) + abs(pos[1] - group.center_y)
        weight = SOCIAL_FRINGE_WEIGHT if dist > group.cohesion_radius else SOCIAL_COHESION_WEIGHT
        if not food_targets:
            hunger = (MAX_HEALTH - agent.health) / MAX_HEALTH
            weight *= max(0.0, 1.0 - hunger)
        score += weight / (1 + dist)
    elif social_target:
        tx, ty, gravity = social_target
        dist = abs(pos[0] - tx) + abs(pos[1] - ty)
        score += SOCIAL_LONE_WEIGHT * gravity / (1 + dist)

    if agent.direction:
        dx, dy = pos[0] - origin[0], pos[1] - origin[1]
        dot = agent.direction[0] * dx + agent.direction[1] * dy
        lost = not food_targets and not agent.last_food_seen
        satiation = 1.0 if lost else (agent.health / MAX_HEALTH) ** 2
        score += MOMENTUM_WEIGHT * max(0.0, dot) * satiation

    if not food_targets and agent.last_food_seen:
        mx, my = agent.last_food_seen
        dist = abs(pos[0] - mx) + abs(pos[1] - my)
        score += FOOD_MEMORY_WEIGHT / (1 + dist)

    return score


def best_move(
    world: World,
    agent: Agent,
    candidates: list[tuple[int, int]],
    food_targets: list[Food],
    group: Group | None,
    social_target: tuple[float, float, float] | None,
) -> tuple[int, int]:
    best_pos = candidates[0]
    best_score = float("-inf")
    for p1 in candidates:
        s1 = score_move(agent, p1, food_targets, group, social_target)
        p2_candidates = world.valid_moves(p1[0], p1[1])
        s2 = max(
            score_move(agent, p2, food_targets, group, social_target, from_pos=p1)
            for p2 in p2_candidates
        )
        combined = s1 + LOOKAHEAD_DISCOUNT * s2
        if combined > best_score:
            best_score = combined
            best_pos = p1
    return best_pos


def lone_social_target(
    world: World, agent: Agent, vision: float
) -> tuple[float, float, float] | None:
    best: tuple[float, float, float] | None = None
    best_score = 0.0

    for group in world.all_groups():
        dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
        if dist <= vision:
            score = group.gravity / (1 + dist)
            if score > best_score:
                best_score = score
                best = (group.center_x, group.center_y, group.gravity)

    for other in world.agents_in_range(agent, vision):
        if other.group_id is None:
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            score = 1.0 / (1 + dist)
            if score > best_score:
                best_score = score
                best = (float(other.x), float(other.y), 1.0)

    return best
