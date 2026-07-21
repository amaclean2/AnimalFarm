from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import (
    ScoredCandidate,
    ScoringContext,
    TIER_BUSY_DRINK,
    TIER_THIRST_FORCED,
    register_scorer,
    scale_urgency,
)
from agents.scoring.urgency import (
    compute_urgencies,
    eligibility_threshold,
    resolve_thirst_explore_goal,
    resolve_water_target,
)


@register_scorer
def score_continue_drink(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if agent.needs.is_drinking or (context.at_river_tile and agent.needs.water < 1.0):
        return ScoredCandidate("drink", TIER_BUSY_DRINK, agent.pos)

    return None


@register_scorer
def score_thirst_explore_forced(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if resolve_water_target(agent, context) is not None:
        return None

    return ScoredCandidate(
        "thirst_explore", TIER_THIRST_FORCED, resolve_thirst_explore_goal(agent)
    )


@register_scorer
def score_seek_water(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    water_target = resolve_water_target(agent, context)

    if water_target is None:
        return None

    urgencies = compute_urgencies(agent)
    urgency = urgencies["thirst"]

    if urgency < eligibility_threshold(agent, "seek_water", urgencies):
        return None

    return ScoredCandidate("seek_water", scale_urgency(urgency), water_target)
