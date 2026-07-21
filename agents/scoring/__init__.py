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

URGENCY_BAND_LOW = 0.05
URGENCY_BAND_HIGH = 0.90

TIER_BUSY_SLEEP = 1.00
TIER_BUSY_HARVEST = 0.99
TIER_BUSY_DRINK = 0.98
TIER_HARVEST_START = 0.97
TIER_THIRST_FORCED = 0.96
TIER_HUNGER_EMERGENCY = 0.95
TIER_REST_ARRIVED = 0.91

TIER_FALLBACK_MATE = 0.02
TIER_FALLBACK_EXPLORE = 0.00


def register_scorer(scorer_function: ScorerFn) -> ScorerFn:
    SCORERS.append(scorer_function)
    return scorer_function


def score_all(agent: "Agent", context: ScoringContext) -> list[ScoredCandidate]:
    return [
        candidate
        for scorer in SCORERS
        if (candidate := scorer(agent, context)) is not None
    ]


def choose_best(agent: "Agent", context: ScoringContext) -> ScoredCandidate:
    return max(score_all(agent, context), key=lambda candidate: candidate.score)


def scale_urgency(raw: float) -> float:
    return URGENCY_BAND_LOW + raw * (URGENCY_BAND_HIGH - URGENCY_BAND_LOW)


from agents.scoring import continuation, fallback, hunger, rest, thirst  # noqa: E402,F401
