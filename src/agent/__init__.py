import math
import random
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from agent.memory import Memory
from agent.needs import NeedState
import config as _cfg
from config import (
    REPRODUCTION_HUNGER_THRESHOLD,
    VISION_RANGE,
    CONTINUATION_BONUS,
)
from food import Food
from tasks import Task

_NEEDS = [
    "hunger",
    "thirst",
    "rest",
    "safety",
    "social",
    "reproduction",
    "curiosity",
]

_RELEVANCE: dict[str, dict[str, float]] = {
    "seek_food": {
        "hunger": 1.0,
        "thirst": 0.0,
        "rest": 0.0,
        "safety": 0.0,
        "social": 0.1,
        "reproduction": 0.0,
        "curiosity": 0.0,
    },
    "drink": {
        "hunger": 0.0,
        "thirst": 1.0,
        "rest": 0.0,
        "safety": 0.0,
        "social": 0.0,
        "reproduction": 0.0,
        "curiosity": 0.0,
    },
    "sleep": {
        "hunger": 0.1,
        "thirst": 0.1,
        "rest": 1.0,
        "safety": 0.0,
        "social": 0.0,
        "reproduction": 0.0,
        "curiosity": 0.0,
    },
    "flee": {
        "hunger": 0.0,
        "thirst": 0.0,
        "rest": 0.0,
        "safety": 1.0,
        "social": 0.3,
        "reproduction": -0.2,
        "curiosity": 0.0,
    },
    "mate": {
        "hunger": 0.0,
        "thirst": 0.0,
        "rest": 0.0,
        "safety": -0.5,
        "social": 0.2,
        "reproduction": 1.0,
        "curiosity": 0.0,
    },
    "explore": {
        "hunger": 0.2,
        "thirst": 0.2,
        "rest": -0.3,
        "safety": -0.5,
        "social": -0.2,
        "reproduction": 0.1,
        "curiosity": 1.0,
    },
}


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    age: int = 0
    alive: bool = True
    is_adult: bool = False
    birth_tick: int = 0
    vision_range: int = VISION_RANGE

    genotype: dict[str, int] = Field(default_factory=dict)
    mutations: list[str] = Field(default_factory=list)

    group_id: UUID | None = None
    carried_food: Food | None = None

    direction: tuple[int, int] | None = None
    active_task: Task | None = None
    path: list[tuple[int, int]] = Field(default_factory=list)
    last_decision_tick: int = 0
    explore_target: tuple[int, int] | None = None
    explore_target_tick: int = 0

    needs: NeedState = Field(default_factory=NeedState)
    memory: Memory = Field(default_factory=Memory)
    decision_log: list[dict] = Field(default_factory=list, exclude=True)

    # --- computed fields so model_dump keeps the fields the frontend expects ---

    @computed_field
    @property
    def hunger(self) -> float:
        return self.needs.hunger

    @computed_field
    @property
    def is_sleeping(self) -> bool:
        return self.needs.is_sleeping

    @computed_field
    @property
    def metabolism(self) -> float:
        return self.needs.metabolism

    @computed_field
    @property
    def rest(self) -> float:
        return self.needs.rest

    @computed_field
    @property
    def water(self) -> float:
        return self.needs.water

    # backward compat for movement.py: nearest recently-observed food position
    @property
    def last_food_seen(self) -> tuple[int, int] | None:
        if not self.memory.food:
            return None
        return max(self.memory.food, key=lambda e: e.added_tick).pos

    # --- lifecycle ---

    def move_to(self, x: int, y: int) -> None:
        self.direction = (x - self.x, y - self.y)
        self.x = x
        self.y = y

    def eat(self) -> None:
        self.needs.eat()
        self.direction = None

    def drink(self) -> None:
        self.needs.drink()

    def die(self) -> None:
        self.alive = False
        self.active_task = None
        self.path = []

    # --- need delegation ---

    def tick_needs(
        self, is_night: bool, tile_quality: float = 1.0, temperature: float = 0.5
    ) -> None:
        self.needs.tick(is_night, tile_quality, temperature)

    def apply_hunger_drain(self, is_river: bool, is_lone: bool) -> None:
        self.needs.apply_hunger_drain(self.age, self.is_adult, is_river, is_lone)

    def drain_uphill(self, elev_gain: float) -> None:
        self.needs.drain_uphill(elev_gain)

    # --- memory delegation ---

    def update_food_memory(self, food_targets: list[Food], tick: int) -> None:
        for food in food_targets:
            self.memory.observe((food.x, food.y), "food", float(food.value), tick)

    def update_rest_memory(
        self, pos: tuple[int, int], quality: float, tick: int
    ) -> None:
        self.memory.observe(pos, "rest", quality, tick)

    # --- reproduction ---

    def is_eligible_to_mate(self) -> bool:
        return (
            self.age >= _cfg.MATURITY_AGE
            and self.needs.hunger >= REPRODUCTION_HUNGER_THRESHOLD
            and not self.needs.is_sleeping
        )

    # --- decision making ---

    def _needs_snapshot(self) -> dict:
        return {
            "hunger": self.needs.hunger,
            "water": self.needs.water,
            "rest": self.needs.rest,
        }

    def choose_action(
        self,
        is_night: bool,
        mate_pos: tuple[int, int] | None,
        explore_goal: tuple[int, int],
        tick: int,
        rest_target: tuple[int, int] | None = None,
    ) -> Task:
        urgencies = self.needs.urgency_vector()
        food_target = self.memory.query("food", tick, urgency=urgencies["hunger"])
        water_target = self.memory.query("water", tick, urgency=urgencies["thirst"])

        candidates = self._feasible_actions(
            food_target, water_target, mate_pos, rest_target
        )

        best_action, best_score = "explore", float("-inf")
        scored: list[dict] = []
        for action in candidates:
            score = sum(urgencies[need] * _RELEVANCE[action][need] for need in _NEEDS)
            is_continuation = bool(self.active_task and self.active_task.name == action)

            if is_continuation:
                score += CONTINUATION_BONUS
            scored.append(
                {
                    "action": action,
                    "score": round(score, 4),
                    "continuation": is_continuation,
                }
            )

            if score > best_score:
                best_score, best_action = score, action

        self.decision_log.append(
            {
                "tick": tick,
                "pos": [self.x, self.y],
                "needs": self._needs_snapshot(),
                "urgencies": {k: round(v, 4) for k, v in urgencies.items()},
                "candidates": sorted(scored, key=lambda s: s["score"], reverse=True),
                "chosen": best_action,
            }
        )

        self.last_decision_tick = tick
        return self._resolve_task(
            best_action,
            food_target,
            water_target,
            mate_pos,
            explore_goal,
            rest_target,
        )

    def _feasible_actions(
        self,
        food_target: tuple[int, int] | None,
        water_target: tuple[int, int] | None,
        mate_pos: tuple[int, int] | None,
        rest_target: tuple[int, int] | None = None,
    ) -> list[str]:
        if self.needs.is_sleeping and self.needs.rest < 1.0 and rest_target:
            return ["sleep"]

        actions = ["explore"]

        if food_target:
            actions.append("seek_food")

        if water_target:
            actions.append("drink")

        if rest_target and self.needs.rest < 1.0:
            actions.append("sleep")

        if mate_pos:
            actions.append("mate")

        return actions

    def _resolve_task(
        self,
        action: str,
        food: tuple[int, int] | None,
        water: tuple[int, int] | None,
        mate: tuple[int, int] | None,
        explore: tuple[int, int],
        rest: tuple[int, int] | None = None,
    ) -> Task:
        goal: tuple[int, int] = {
            "seek_food": food,
            "drink": water,
            "sleep": rest,
            "mate": mate,
            "explore": explore,
        }.get(action, explore)
        return Task(priority=0, name=action, goal_pos=goal)

    def explore_goal(
        self, world_width: int, world_height: int, tick: int = 0
    ) -> tuple[int, int]:
        arrived = self.explore_target is not None and (
            abs(self.x - self.explore_target[0]) + abs(self.y - self.explore_target[1])
            <= 2
        )
        stale = tick - self.explore_target_tick > 40

        if self.explore_target is None or arrived or stale:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.randint(15, 35)
            self.explore_target = (
                max(0, min(world_width - 1, int(self.x + dist * math.cos(angle)))),
                max(0, min(world_height - 1, int(self.y + dist * math.sin(angle)))),
            )
            self.explore_target_tick = tick

        return self.explore_target
