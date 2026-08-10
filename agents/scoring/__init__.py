from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pos import Pos

if TYPE_CHECKING:
    from agents.agent import Agent
    from plant import Plant
    from world import World


@dataclass(frozen=True)
class ScoringContext:
    world: "World | None"
    mate_pos: Pos | None
    at_river_tile: bool
    local_plant: "Plant | None"
    occupied_tiles: set[Pos] | None


@dataclass(frozen=True)
class ScoredCandidate:
    task_name: str
    score: float
    goal_pos: Pos


ScorerFn = Callable[["Agent", ScoringContext], "ScoredCandidate | None"]

SCORERS: list[ScorerFn] = []

URGENCY_BAND_HIGH = 0.90

TIER_BUSY = 1.00
TIER_HARVEST_START = 0.97
TIER_HUNGER_EMERGENCY = 0.95
TIER_START_REST = 0.91

TIER_FALLBACK_MATE = 0.02
TIER_FALLBACK_EXPLORE = 0.015


def register_scorer(scorer_function: ScorerFn) -> ScorerFn:
    SCORERS.append(scorer_function)
    return scorer_function


def score_all(agent: "Agent", context: ScoringContext) -> list[ScoredCandidate]:
    return [
        candidate
        for scorer in SCORERS
        if (candidate := scorer(agent, context)) is not None
    ]


def scale_urgency(raw: float) -> float:
    return raw * URGENCY_BAND_HIGH


from agents.scoring import (
    continuation,
    fallback,
    hunger,
    rest,
    thirst,
)  # noqa: E402,F401
