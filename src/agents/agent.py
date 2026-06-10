import math
import random
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from agents.memory import Memory
from agents.needs import NeedState
import config as _cfg
import event_bus
from events import Event
from config import (
    MATING_COOLDOWN,
    REPRODUCTION_HUNGER_THRESHOLD,
    VISION_RANGE,
    WORLD_WIDTH,
    WORLD_HEIGHT,
)
from genome import default_genome
from pos import Pos
from tasks import Task

task_to_need_map: dict[str, str] = {
    "seek_food": "hunger",
    "harvest_food": "hunger",
    "seek_water": "thirst",
    "drink": "thirst",
    "thirst_explore": "thirst",
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

    last_mated_tick: int = -(MATING_COOLDOWN + 1)

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
        self.x = pos.x
        self.y = pos.y

    def die(self) -> None:
        self.alive = False
        self.active_task = None
        self.path = []
        self.planned_steps = []
        self.needs.harvest_count = 0
        self.needs.is_drinking = False

    def harvest(self) -> bool:
        if self.needs.harvest_count == 0:
            return False

        self.age += 1

        if self.needs.harvest_count == 1:
            self.needs.harvest()
            self.needs.eat()
            event_bus.publish(
                Event("agent_ate", {"agent": self.model_dump(mode="json")})
            )
            return True

        self.needs.harvest()
        return False

    def drink(self) -> None:
        if self.needs.is_drinking:
            self.age += 1
            self.needs.drink()
            event_bus.publish(Event("agent_drank", {"agent_id": str(self.id)}))

    def should_die(self) -> bool:
        return (
            self.needs.hunger <= 0
            or self.needs.water <= 0
            or self.needs.rest <= 0
            or self.age >= _cfg.MAX_AGE
        )

    def sleep_if_ready(self, at_rest_target: bool, in_river: bool = False) -> None:
        if (
            self.active_task
            and self.active_task.name == "sleep"
            and at_rest_target
            and not in_river
        ):
            self.needs.is_sleeping = True

    def needs_replan(self, top_task: Task) -> bool:
        return (
            self.active_task is None
            or top_task.name != self.active_task.name
            or top_task.goal_pos != self.active_task.goal_pos
            or not self.path
        )

    def apply_rest_drain(self, is_night: bool, temperature: float = 15.0) -> None:
        self.needs.apply_rest_drain(is_night, temperature)

    def sleep(self, tile_quality: float = 1.0) -> bool:
        if not self.needs.is_sleeping:
            return False

        self.age += 1
        sleeping_complete = self.needs.sleep(tile_quality)

        if sleeping_complete:
            self.rest_target = None
            return True

        return False

    def apply_hunger_drain(self, is_river: bool) -> None:
        self.needs.apply_hunger_drain(self.age, self.is_adult, is_river)

    def apply_thirst_drain(self) -> None:
        self.needs.apply_thirst_drain()

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

        if self.rest_target is not None and self.rest_target in sleeping_tiles:
            self.rest_target = None

        if (
            self.rest_target is None
            and visible_rest
            and visible_rest not in sleeping_tiles
        ):
            self.rest_target = visible_rest

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
        at_river_tile: bool = False,
        plant_labor: int | None = None,
    ) -> Task:
        if self.needs.is_sleeping:
            return Task(priority=0, name="sleep", goal_pos=self.pos)

        if self.needs.harvest_count > 0:
            return Task(priority=0, name="harvest_food", goal_pos=self.pos)

        if self.needs.is_drinking:
            return Task(priority=0, name="drink", goal_pos=self.pos)

        if at_river_tile:
            return Task(priority=0, name="drink", goal_pos=self.pos)

        if (
            plant_labor is not None
            and self.active_task is not None
            and self.active_task.name == "seek_food"
        ):
            return Task(priority=0, name="harvest_food", goal_pos=self.pos)

        food_target = self.memory.query("food", tick)
        water_target = self.memory.query("water", tick)
        has_visible_water = bool(visible_water)

        if not water_target and not has_visible_water:
            return Task(priority=0, name="thirst_explore", goal_pos=thirst_explore_goal)

        if self.active_task and self.active_task.name == "thirst_explore":
            return Task(
                priority=0,
                name="seek_water",
                goal_pos=water_target or thirst_explore_goal,
            )

        if water_target:
            ticks_to_empty = self.needs.water / _cfg.WATER_BASE_DRAIN
            dist = abs(water_target.x - self.x) + abs(water_target.y - self.y)
            if dist + 2 >= ticks_to_empty:
                return Task(priority=0, name="seek_water", goal_pos=water_target)

        if food_target:
            ticks_to_empty = self.needs.hunger / _cfg.HUNGER_BASE_DRAIN
            dist = abs(food_target.x - self.x) + abs(food_target.y - self.y)
            if dist + 2 >= ticks_to_empty:
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
        is_idle = active_task_name in (None, "explore")

        if is_idle:
            active_needs = {n: s for n, s in raw.items() if s >= idle_threshold}
        else:
            current_need = task_to_need_map.get(active_task_name, "")
            current_u = raw.get(current_need, 0.0)
            active_needs = {
                n: s for n, s in raw.items() if s >= current_u + breakaway_margin
            }

        scored_tasks: dict[str, float] = {}

        if "thirst" in active_needs:
            if has_visible_water or water_target:
                scored_tasks["seek_water"] = thirst_u
            else:
                scored_tasks["thirst_explore"] = thirst_u

        if "hunger" in active_needs and food_target:
            scored_tasks["seek_food"] = hunger_u

        if "rest" in active_needs:
            scored_tasks["sleep"] = rest_u

        if scored_tasks:
            best = max(scored_tasks, key=scored_tasks.__getitem__)
            return self._make_task(
                best,
                food_target,
                water_target,
                explore_goal,
                thirst_explore_goal,
                rest_target,
            )

        if not is_idle and active_task_name:
            need_name = task_to_need_map.get(active_task_name, "")
            need_urgency = raw.get(need_name, 0.0)
            has_target = (
                active_task_name != "seek_food" or food_target is not None
            ) and (active_task_name != "seek_water" or water_target is not None)
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
            "explore": explore,
            "thirst_explore": thirst_explore,
        }.get(action)
        return Task(priority=0, name=action, goal_pos=goal or explore)

    def get_explore_goal(self, tick: int = 0) -> Pos:
        arrived = self.explore_target is not None and (
            abs(self.x - self.explore_target.x) + abs(self.y - self.explore_target.y)
            <= 2
        )
        stale = tick - self.explore_target_tick > 40

        if self.explore_target is None or arrived or stale:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.randint(15, 35)
            self.explore_target = Pos(
                max(0, min(WORLD_WIDTH - 1, int(self.x + dist * math.cos(angle)))),
                max(0, min(WORLD_HEIGHT - 1, int(self.y + dist * math.sin(angle)))),
            )
            self.explore_target_tick = tick

        return self.explore_target

    def tick_movement(
        self,
        is_river_tile: Callable[[Pos], bool],
        occupied: set[Pos],
        tick_count: int,
        elevation_at: Callable[[Pos], float],
        is_night: bool,
        temperature: float,
    ) -> None:
        old_pos = self.pos

        if not self.planned_steps:
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

                if self.needs.is_sleeping:
                    self.planned_steps.clear()
                elif self.pos != old_pos:
                    elev_gain = elevation_at(self.pos) - elevation_at(old_pos)

                    if elev_gain > 0:
                        self.needs.drain_uphill(elev_gain)

        occupied.discard(old_pos)
        occupied.add(self.pos)
        self.age += 1

        self.apply_rest_drain(is_night, temperature)
        self.apply_hunger_drain(is_river_tile(self.pos))
        self.apply_thirst_drain()

        event_bus.publish(Event("agent_moved", {"agent": self.model_dump(mode="json")}))

    def get_thirst_explore_goal(self, tick: int = 0) -> Pos:
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
                max(0, min(WORLD_WIDTH - 1, int(self.x + dist * math.cos(angle)))),
                max(0, min(WORLD_HEIGHT - 1, int(self.y + dist * math.sin(angle)))),
            )
            self.thirst_explore_target_tick = tick

        return self.thirst_explore_target
