from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import (
    ScoredCandidate,
    ScoringContext,
    TIER_FALLBACK_EXPLORE,
    TIER_FALLBACK_MATE,
    register_scorer,
)
from agents.scoring.urgency import resolve_explore_goal


@register_scorer
def score_mate(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:
    if context.mate_pos is None:
        return None

    return ScoredCandidate("mate", TIER_FALLBACK_MATE, context.mate_pos)


@register_scorer
def score_explore_default(agent: "Agent", context: ScoringContext) -> ScoredCandidate:
    return ScoredCandidate("explore", TIER_FALLBACK_EXPLORE, resolve_explore_goal(agent))
