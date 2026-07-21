from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import (
    ScoredCandidate,
    ScoringContext,
    TIER_BUSY_SLEEP,
    TIER_REST_ARRIVED,
    register_scorer,
    scale_urgency,
)
from agents.scoring.urgency import (
    compute_urgencies,
    eligibility_threshold,
    resolve_rest_target,
)


@register_scorer
def score_continue_sleep(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if not agent.needs.is_sleeping:
        return None

    return ScoredCandidate("sleep", TIER_BUSY_SLEEP, agent.pos)


@register_scorer
def score_rest_arrived(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if context.at_river_tile:
        return None
        
    if agent.active_task.name != "seek_rest":
        return None

    rest_target = resolve_rest_target(agent)

    if rest_target is None or agent.pos != rest_target:
        return None

    return ScoredCandidate("sleep", TIER_REST_ARRIVED, agent.pos)


@register_scorer
def score_seek_rest(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    rest_target = resolve_rest_target(agent)

    if rest_target is None:
        return None

    urgencies = compute_urgencies(agent)
    urgency = urgencies["rest"]

    if urgency < eligibility_threshold(agent, "seek_rest", urgencies):
        return None

    return ScoredCandidate("seek_rest", scale_urgency(urgency), rest_target)
