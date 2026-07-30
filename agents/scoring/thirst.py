from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import (
    ScoredCandidate,
    ScoringContext,
    TIER_BUSY,
    register_scorer,
    scale_urgency,
)
from agents.scoring.urgency import (
    compute_urgencies,
    resolve_thirst_explore_goal,
    resolve_water_target,
)


@register_scorer
def score_continue_drink(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if agent.needs.is_drinking or (context.at_river_tile and agent.needs.water > 0.0):
        return ScoredCandidate("drink", TIER_BUSY, agent.pos)

    return None


@register_scorer
def score_thirst_explore_forced(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if agent.memory.water:
        return None

    return ScoredCandidate(
        "thirst_explore", TIER_BUSY, resolve_thirst_explore_goal(agent)
    )


@register_scorer
def score_seek_water(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    water_target = resolve_water_target(agent, context)

    if water_target is None:
        return None

    urgencies = compute_urgencies(agent)
    urgency = urgencies["thirst"]

    return ScoredCandidate("seek_water", scale_urgency(urgency), water_target)
