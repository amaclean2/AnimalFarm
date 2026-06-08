import math
import random
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from agents.memory import Memory
from agents.needs import NeedState
import config as _cfg
from config import (
    MATING_COOLDOWN,
    REPRODUCTION_HUNGER_THRESHOLD,
    VISION_RANGE,
    WORLD_WIDTH,
)
from genome import default_genome
from pos import Pos
from tasks import Task

_TASK_TO_NEED: dict[str, str] = {
    "seek_food": "hunger",
    "seek_water": "thirst",
    "drink": "thirst",
    "sleep": "rest",
}


def _urgency(level: float) -> float:
    return (1.0 - level) ** 2


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
    behavioral_genome: dict[str, float] = Field(default_factory=default_genome)
    offspring_count: int = 0

    carried_food: int = 0

    harvest_count: int = 0

    last_mated_tick: int = -(MATING_COOLDOWN + 1)

    direction: tuple[int, int] | None = None
    active_task: Task | None = None
    path: list[Pos] = Field(default_factory=list)
    next_decision_tick: int = 0
    planned_steps: list[Pos] = Field(default_factory=list)
    explore_target: Pos | None = None
    explore_target_tick: int = 0
    thirst_explore_target: Pos | None = None
    thirst_explore_target_tick: int = 0
    rest_target: Pos | None = None

    needs: NeedState = Field(default_factory=NeedState)
    memory: Memory = Field(default_factory=Memory)

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

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)

    def get_pos_idx(self) -> int:
        return self.y * WORLD_WIDTH + self.x

    @property
    def last_food_seen(self) -> Pos | None:
        if not self.memory.food:
            return None
        return max(self.memory.food, key=lambda e: e.added_tick).pos

    def move_to(self, pos: Pos) -> None:
        self.direction = (pos.x - self.x, pos.y - self.y)
        self.x = pos.x
        self.y = pos.y

    def clear_direction(self) -> None:
        self.direction = None

    def eat(self) -> None:
        self.needs.eat()
        self.clear_direction()

    def drink(self) -> None:
        self.needs.drink()

    def die(self) -> None:
        self.alive = False
        self.active_task = None
        self.path = []
        self.planned_steps = []
        self.harvest_count = 0

    def begin_harvest(self, plant) -> None:
        self.harvest_count = plant.ticks_per_fruit

    def should_die(self) -> bool:
        return (
            self.hunger <= 0
            or self.needs.water <= 0
            or self.needs.rest <= 0
            or self.age >= _cfg.MAX_AGE
        )

    def tick_sleep(self) -> None:
        was = self.needs.is_sleeping
        self.needs.is_sleeping = was and self.needs.rest < 1.0

    def sleep_if_ready(self, at_rest_target: bool, is_river: bool = False) -> None:
        if (
            self.active_task
            and self.active_task.name == "sleep"
            and at_rest_target
            and not is_river
        ):
            self.needs.is_sleeping = True

    def needs_replan(self, top_task: Task) -> bool:
        return (
            self.active_task is None
            or top_task.name != self.active_task.name
            or top_task.goal_pos != self.active_task.goal_pos
            or not self.path
        )

    def increment_needs(
        self, is_night: bool, tile_quality: float = 1.0, temperature: float = 0.5
    ) -> None:
        self.needs.tick(is_night, tile_quality, temperature)

    def apply_hunger_drain(self, is_river: bool) -> None:
        self.needs.apply_hunger_drain(self.age, self.is_adult, is_river)

    def drain_uphill(self, elev_gain: float) -> None:
        self.needs.drain_uphill(elev_gain)

    def update_food_memory(self, plant_targets: list, tick: int) -> None:
        for plant in plant_targets:
            self.memory.observe(plant.pos, "food", 1.0, tick)

    def update_water_memory(self, visible_water: list[Pos], tick: int) -> None:
        for pos in visible_water:
            self.memory.observe(pos, "water", 1.0, tick)

    def update_rest_target(
        self,
        visible_rest: Pos | None,
        sleeping_tiles: set[Pos],
    ) -> None:
        if self.needs.rest >= 0.8:
            self.rest_target = None
            return

        if visible_rest and visible_rest not in sleeping_tiles:
            self.rest_target = visible_rest
        elif self.rest_target is not None and self.rest_target in sleeping_tiles:
            self.rest_target = None

    def is_eligible_to_mate(self, tick: int) -> bool:
        return (
            self.age >= _cfg.MATURITY_AGE
            and self.needs.hunger >= REPRODUCTION_HUNGER_THRESHOLD
            and not self.needs.is_sleeping
            and tick - self.last_mated_tick >= MATING_COOLDOWN
        )

    def choose_action(
        self,
        mate_pos: Pos | None,
        explore_goal: Pos,
        thirst_explore_goal: Pos,
        tick: int,
        visible_water: list[Pos] | None = None,
        rest_target: Pos | None = None,
    ) -> Task:
        food_target = self.memory.query("food", tick)
        water_target = self.memory.query("water", tick)
        has_visible_water = bool(visible_water)

        if not water_target and not has_visible_water:
            return Task(priority=0, name="thirst_explore", goal_pos=thirst_explore_goal)

        if self.active_task and self.active_task.name == "thirst_explore":
            if has_visible_water:
                return Task(
                    priority=0,
                    name="drink",
                    goal_pos=water_target or thirst_explore_goal,
                )
            return Task(priority=0, name="seek_water", goal_pos=water_target)

        if water_target:
            ticks_to_empty = self.needs.water / _cfg.WATER_BASE_DRAIN
            dist = abs(water_target.x - self.x) + abs(water_target.y - self.y)
            if dist >= ticks_to_empty:
                return Task(priority=0, name="seek_water", goal_pos=water_target)

        if food_target:
            ticks_to_empty = self.needs.hunger / _cfg.HUNGER_BASE_DRAIN
            dist = abs(food_target.x - self.x) + abs(food_target.y - self.y)
            if dist >= ticks_to_empty:
                return Task(priority=0, name="seek_food", goal_pos=food_target)

        if self.needs.rest <= _cfg.REST_SAFETY_BUFFER_FRAC:
            return Task(priority=0, name="sleep", goal_pos=self.pos)

        thirst_u = _urgency(self.needs.water)
        hunger_u = _urgency(self.needs.hunger)
        rest_u = _urgency(self.needs.rest)

        raw = {"thirst": thirst_u, "hunger": hunger_u, "rest": rest_u}

        idle_threshold = self.behavioral_genome["idle_threshold"]
        breakaway_margin = self.behavioral_genome["breakaway_margin"]
        active_task_name = self.active_task.name if self.active_task else None
        is_idle = active_task_name in (None, "explore", "thirst_explore")

        if is_idle:
            active_needs = {n: s for n, s in raw.items() if s >= idle_threshold}
        else:
            current_need = _TASK_TO_NEED.get(active_task_name, "")
            current_u = raw.get(current_need, 0.0)
            active_needs = {
                n: s for n, s in raw.items() if s >= current_u + breakaway_margin
            }

        candidates: dict[str, float] = {}

        if "thirst" in active_needs:
            if has_visible_water:
                candidates["drink"] = thirst_u
            elif water_target:
                candidates["seek_water"] = thirst_u

        if "hunger" in active_needs and food_target:
            candidates["seek_food"] = hunger_u

        if "rest" in active_needs:
            candidates["sleep"] = rest_u

        if candidates:
            best = max(candidates, key=candidates.__getitem__)
            return self._make_task(
                best,
                food_target,
                water_target,
                explore_goal,
                thirst_explore_goal,
                rest_target,
            )

        if not is_idle and active_task_name:
            need_name = _TASK_TO_NEED.get(active_task_name, "")
            need_urgency = raw.get(need_name, 0.0)
            has_target = (
                active_task_name != "seek_food" or food_target is not None
            ) and (
                active_task_name not in ("seek_water", "drink")
                or water_target is not None
            )
            if need_urgency >= idle_threshold and has_target:
                return self._make_task(
                    active_task_name,
                    food_target,
                    water_target,
                    explore_goal,
                    thirst_explore_goal,
                    rest_target,
                )

        if mate_pos and self.is_eligible_to_mate(tick):
            return Task(priority=0, name="mate", goal_pos=mate_pos)

        return Task(priority=0, name="explore", goal_pos=explore_goal)

    def _make_task(
        self,
        action: str,
        food: Pos | None,
        water: Pos | None,
        explore: Pos,
        thirst_explore: Pos,
        rest: Pos | None,
    ) -> Task:
        if action == "sleep":
            return Task(priority=0, name="sleep", goal_pos=rest or self.pos)
        goal: Pos | None = {
            "seek_food": food,
            "seek_water": water,
            "drink": water,
            "explore": explore,
            "thirst_explore": thirst_explore,
        }.get(action)
        return Task(priority=0, name=action, goal_pos=goal or explore)

    def explore_goal(self, world_width: int, world_height: int, tick: int = 0) -> Pos:
        arrived = self.explore_target is not None and (
            abs(self.x - self.explore_target.x) + abs(self.y - self.explore_target.y)
            <= 2
        )
        stale = tick - self.explore_target_tick > 40

        if self.explore_target is None or arrived or stale:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.randint(15, 35)
            self.explore_target = Pos(
                max(0, min(world_width - 1, int(self.x + dist * math.cos(angle)))),
                max(0, min(world_height - 1, int(self.y + dist * math.sin(angle)))),
            )
            self.explore_target_tick = tick

        return self.explore_target

    def tick_movement(
        self,
        is_river_tile: Callable[[Pos], bool],
        occupied: set[Pos],
        tick_count: int,
        tile_quality: float,
    ) -> None:
        old_pos = self.pos
        was_sleeping = self.is_sleeping

        self.tick_sleep()

        if self.is_sleeping:
            self.planned_steps.clear()
        elif self.harvest_count > 0:
            self.planned_steps.clear()
            self.next_decision_tick = tick_count + 1
        elif was_sleeping:
            self.planned_steps.clear()
            self.next_decision_tick = tick_count
        elif not self.planned_steps:
            self.next_decision_tick = tick_count
        else:
            step = self.planned_steps[0]

            if step != self.pos and step in occupied:
                self.planned_steps.clear()
                self.next_decision_tick = tick_count
            else:
                self.planned_steps.pop(0)

                if self.path and self.path[0] == step:
                    self.path.pop(0)

                self.move_to(step)
                at_rest_target = (
                    self.rest_target is None or self.pos == self.rest_target
                )
                self.sleep_if_ready(at_rest_target, is_river_tile(self.pos))

                if self.is_sleeping:
                    self.planned_steps.clear()

        if was_sleeping and not self.is_sleeping:
            self.rest_target = None

        occupied.discard(old_pos)
        occupied.add(self.pos)
        self.age += 1

    def thirst_explore_goal(
        self, world_width: int, world_height: int, tick: int = 0
    ) -> Pos:
        arrived = self.thirst_explore_target is not None and (
            abs(self.x - self.thirst_explore_target.x)
            + abs(self.y - self.thirst_explore_target.y)
            <= 3
        )
        stale = tick - self.thirst_explore_target_tick > 80

        if self.thirst_explore_target is None or arrived or stale:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.randint(40, 70)
            self.thirst_explore_target = Pos(
                max(0, min(world_width - 1, int(self.x + dist * math.cos(angle)))),
                max(0, min(world_height - 1, int(self.y + dist * math.sin(angle)))),
            )
            self.thirst_explore_target_tick = tick

        return self.thirst_explore_target
