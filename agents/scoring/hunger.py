from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import (
    ScoredCandidate,
    ScoringContext,
    TIER_BUSY_HARVEST,
    TIER_HARVEST_START,
    TIER_HUNGER_EMERGENCY,
    register_scorer,
    scale_urgency,
)
from agents.scoring.urgency import (
    compute_urgencies,
    eligibility_threshold,
    resolve_explore_goal,
    resolve_food_target,
)
from config import HUNGER_BASE_DRAIN


@register_scorer
def score_continue_harvest(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if agent.needs.harvest_count <= 0:
        return None
        
    return ScoredCandidate("harvest_food", TIER_BUSY_HARVEST, agent.pos)


@register_scorer
def score_harvest_start(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if context.local_plant is None:
        return None

    if agent.active_task.name not in ("seek_food", "harvest_food"):
        return None

    if agent.needs.hunger >= 1.0:
        return None

    return ScoredCandidate("harvest_food", TIER_HARVEST_START, agent.pos)


@register_scorer
def score_hunger_emergency(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    food_target = resolve_food_target(agent, context)

    if food_target is None:
        return None

    ticks_to_empty = agent.needs.hunger / HUNGER_BASE_DRAIN
    dist = abs(food_target.x - agent.x) + abs(food_target.y - agent.y)

    if dist + 2 < ticks_to_empty:
        return None

    return ScoredCandidate("seek_food", TIER_HUNGER_EMERGENCY, food_target)


@register_scorer
def score_seek_food(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    food_target = resolve_food_target(agent, context)

    if food_target is None:
        return None

    urgencies = compute_urgencies(agent)
    urgency = urgencies["hunger"]

    if urgency < eligibility_threshold(agent, "seek_food", urgencies):
        return None

    return ScoredCandidate("seek_food", scale_urgency(urgency), food_target)


@register_scorer
def score_explore_hunger(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if resolve_food_target(agent, context) is not None:
        return None

    urgencies = compute_urgencies(agent)
    urgency = urgencies["hunger"]

    if urgency < eligibility_threshold(agent, "explore", urgencies):
        return None

    return ScoredCandidate("explore", scale_urgency(urgency), resolve_explore_goal(agent))
