from __future__ import annotations

import copy
import random
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from config import CORE_TEMP_DEATH_MARGIN_C, IDEAL_CORE_TEMP_C

if TYPE_CHECKING:
    from agents.agent import Agent

NEED_BANDS = 5

ACTIONS: tuple[str, ...] = (
    "drink",
    "seek_water",
    "thirst_explore",
    "eat",
    "harvest_food",
    "seek_food",
    "sleep",
    "seek_rest",
    "explore",
    "mate",
)


def convert_to_band(value: float) -> int:
    return int(value * NEED_BANDS)


def state_key(agent: "Agent") -> str:
    needs = agent.needs
    temp_deviation = (
        abs(needs.core_temperature - IDEAL_CORE_TEMP_C) / CORE_TEMP_DEATH_MARGIN_C
    )

    is_near_water = agent.memory.query("water", agent.pos, max_dist=1) is not None
    is_near_food = agent.memory.query("food", agent.pos, max_dist=1) is not None

    return (
        f"hunger={convert_to_band(needs.hunger)} "
        f"thirst={convert_to_band(needs.thirst)} "
        f"rest={convert_to_band(needs.rest)} "
        f"temp={convert_to_band(temp_deviation)} "
        f"near_water={is_near_water} "
        f"near_food={is_near_food}"
    )


class ScoringMatrix(BaseModel):
    cap: int = 2000
    learning_rate: float = 0.1
    discount: float = 0.9
    epsilon: float = 0.05
    table: dict[str, dict[str, float]] = Field(default_factory=dict)
    start_snapshot: dict[str, dict[str, float]] | None = None

    def capture_snapshot(self) -> None:
        self.start_snapshot = copy.deepcopy(self.table)

    def compare_snapshots(
        self, limit: int = 200
    ) -> list[tuple[str, str, float | None, float, float | None]]:
        if self.start_snapshot is None:
            return []

        changes: list[tuple[str, str, float | None, float, float | None]] = []
        for state, actions in self.table.items():
            before_row = self.start_snapshot.get(state, {})
            for action, after in actions.items():
                before = before_row.get(action)
                if before == after:
                    continue
                delta = after - before if before is not None else None
                changes.append((state, action, before, after, delta))

        changes.sort(
            key=lambda entry: abs(entry[4]) if entry[4] is not None else -1.0,
            reverse=True,
        )
        return changes[:limit]

    def get_value(self, state: str, action: str) -> float:
        row = self.table.pop(state, None) or {}

        if action not in row:
            row[action] = random.random()

        self.table[state] = row
        self.evict_if_needed()

        return row[action]

    def choose_action(self, state: str, available_actions: list[str]) -> str:
        if random.random() < self.epsilon:
            return random.choice(available_actions)

        return max(
            available_actions,
            key=lambda action: self.get_value(state, action),
        )

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        next_available_actions: list[str],
    ) -> None:
        current = self.get_value(state, action)

        best_next_q = max(
            self.get_value(next_state, next_action)
            for next_action in next_available_actions
        )

        self.table[state][action] = current + self.learning_rate * (
            reward + self.discount * best_next_q - current
        )

    def evict_if_needed(self) -> None:
        while len(self.table) > self.cap:
            self.table.pop(next(iter(self.table)))
