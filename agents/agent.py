import math
import random
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from agents.memory import Memory
from agents.needs import NeedState
import event_bus
from events import Event
from config import (
    HUNGER_BASE_DRAIN,
    MATING_COOLDOWN,
    MAX_AGE,
    MATURITY_AGE,
    VISION_RANGE,
    WORLD_WIDTH,
    WORLD_HEIGHT,
)
from genome import default_genome
from pathfinding import astar
from plant import Plant
from pos import Pos
from tasks import Task
from world import World

task_to_need_map: dict[str, str] = {
    "seek_food": "hunger",
    "harvest_food": "hunger",
    "seek_water": "thirst",
    "drink": "thirst",
    "thirst_explore": "thirst",
    "sleep": "rest",
    "seek_rest": "rest",
}


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    age: int = 0
    alive: bool = True
    birth_tick: int = 0
    vision_range: int = VISION_RANGE

    behavioral_genome: dict[str, float] = Field(default_factory=default_genome)
    offspring_count: int = 0

    last_mated_tick: int = -(MATING_COOLDOWN + 1)

    active_task: Task = Field(
        default_factory=lambda: Task(priority=100, name="explore", goal_pos=Pos(0, 0))
    )
    path: list[Pos] = Field(default_factory=list)
    next_decision_tick: int = 0
    planned_steps: list[Pos] = Field(default_factory=list)
    needs: NeedState = Field(default_factory=NeedState)
    memory: Memory = Field(default_factory=Memory)

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)

    def get_pos_idx(self) -> int:
        return self.y * WORLD_WIDTH + self.x

    @property
    def last_food_seen(self) -> Pos | None:
        return self.memory.query("food", self.pos)

    def move_to(self, pos: Pos) -> None:
        self.x = pos.x
        self.y = pos.y

    def die(self) -> None:
        self.alive = False
        self.active_task = Task(priority=100, name="explore", goal_pos=self.pos)
        self.path = []
        self.planned_steps = []
        self.needs.harvest_count = 0
        self.needs.is_drinking = False

    def should_die(self) -> bool:
        return (
            self.needs.hunger <= 0
            or self.needs.water <= 0
            or self.needs.rest <= 0
            or self.age >= MAX_AGE
        )

    def needs_replan(self, priority_task: Task) -> bool:
        return (
            priority_task.name != self.active_task.name
            or priority_task.goal_pos != self.active_task.goal_pos
            or not self.path
        )

    def sleep(self, tile_quality: float = 1.0) -> bool:
        self.age += 1
        sleeping_complete = self.needs.sleep(tile_quality)
        event_bus.publish(
            Event("agent_sleeping", {"agent": self.model_dump(mode="json")})
        )

        return sleeping_complete

    def harvest(self) -> bool:
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

    def apply_thirst_drain(self) -> None:
        self.needs.apply_thirst_drain()

    def drink(self) -> None:
        self.age += 1
        self.needs.drink()
        event_bus.publish(Event("agent_drank", {"agent_id": str(self.id)}))

    def update_memory(self, snapshot: "VisionSnapshot") -> None:
        for plant in snapshot.food_targets:
            self.memory.observe(plant.pos, "food", self.pos)

        for pos in snapshot.visible_water:
            self.memory.observe(pos, "water", self.pos)

        if snapshot.visible_rest is not None:
            self.memory.observe(snapshot.visible_rest, "rest", self.pos)

    def is_eligible_to_mate(self, tick_count: int) -> bool:
        return (
            self.age >= MATURITY_AGE
            and not self.needs.is_sleeping
            and (tick_count - self.last_mated_tick) >= MATING_COOLDOWN
        )

    def calculate_urgencies(self):
        water_resources = self.memory.water
        closest_water_resource = (
            min(
                water_resources,
                key=lambda e: abs(e.x - self.x) + abs(e.y - self.y),
            )
            if water_resources
            else None
        )
        closest_water_resource_dist = (
            abs(closest_water_resource.x - self.x)
            + abs(closest_water_resource.y - self.y)
            if closest_water_resource is not None
            else None
        )

        thirst_urgency = (1.0 - self.needs.water) ** 2

        if (
            closest_water_resource_dist is not None
            and closest_water_resource_dist + 2
            >= self.needs.get_ticks_to_empty("water")
        ):
            thirst_urgency = 1.0

        rest_urgency = (1.0 - self.needs.rest) ** 2
        max_dist_to_rest = self.needs.get_ticks_to_empty("rest")

        reachable_rest = self.memory.query("rest", self.pos, max_dist=max_dist_to_rest)

        if self.memory.rest and reachable_rest is None:
            rest_urgency = 1.0

        return {
            "thirst": thirst_urgency,
            "hunger": (1.0 - self.needs.hunger) ** 2,
            "rest": rest_urgency,
        }

    def choose_action(
        self,
        mate_pos: Pos | None,
        at_river_tile: bool = False,
        local_plant: Plant | None = None,
        occupied_tiles: set[Pos] | None = None,
    ) -> Task:
        active_task_name = self.active_task.name
        is_idle = active_task_name == "explore"

        if self.needs.is_sleeping:
            return Task(priority=0, name="sleep", goal_pos=self.pos)

        if self.needs.harvest_count > 0:
            return Task(priority=0, name="harvest_food", goal_pos=self.pos)

        if self.needs.is_drinking or (at_river_tile and self.needs.water < 1.0):
            return Task(priority=0, name="drink", goal_pos=self.pos)

        if (
            local_plant is not None
            and active_task_name in ("seek_food", "harvest_food")
            and self.needs.hunger < 1.0
        ):
            return Task(priority=0, name="harvest_food", goal_pos=self.pos)

        rest_ticks_to_empty = self.needs.get_ticks_to_empty("rest")

        food_target = self.memory.query("food", self.pos, exclude=occupied_tiles)
        water_target = self.memory.query("water", self.pos)
        if water_target and occupied_tiles and water_target in occupied_tiles:
            water_target = self.memory.query("water", self.pos, exclude={water_target})
        rest_target = self.memory.query("rest", self.pos, max_dist=rest_ticks_to_empty)

        if (
            active_task_name != "thirst_explore"
            or self.active_task.goal_pos == self.pos
        ):
            thirst_explore_target = self.get_thirst_explore_goal()
        else:
            thirst_explore_target = self.active_task.goal_pos

        if not water_target:
            return Task(
                priority=0, name="thirst_explore", goal_pos=thirst_explore_target
            )

        if food_target:
            ticks_to_empty = self.needs.hunger / HUNGER_BASE_DRAIN
            dist = abs(food_target.x - self.x) + abs(food_target.y - self.y)

            if dist + 2 >= ticks_to_empty:
                return Task(priority=0, name="seek_food", goal_pos=food_target)

        if (
            self.pos == rest_target
            and not at_river_tile
            and active_task_name == "seek_rest"
        ):
            return Task(priority=0, name="sleep", goal_pos=self.pos)

        urgency_map = self.calculate_urgencies()
        idle_threshold = self.behavioral_genome["idle_threshold"]

        if is_idle:
            urgent_needs = {n: s for n, s in urgency_map.items() if s >= idle_threshold}
        else:
            current_need = task_to_need_map.get(active_task_name, "")
            current_urgency = urgency_map.get(current_need, 0.0)

            breakaway_margin = self.behavioral_genome["breakaway_margin"]
            urgent_needs = {
                n: s
                for n, s in urgency_map.items()
                if s >= current_urgency + breakaway_margin
            }

        scored_tasks: dict[str, float] = {}

        for need, urgency in urgent_needs.items():
            match need:
                case "thirst":
                    if water_target:
                        scored_tasks["seek_water"] = urgency
                    else:
                        scored_tasks["thirst_explore"] = urgency
                case "hunger":
                    if food_target:
                        scored_tasks["seek_food"] = urgency
                    else:
                        scored_tasks["explore"] = urgency
                case "rest":
                    if rest_target:
                        scored_tasks["seek_rest"] = urgency

        if active_task_name != "explore" or self.active_task.goal_pos == self.pos:
            explore_target = self.get_explore_goal()
        else:
            explore_target = self.active_task.goal_pos

        if scored_tasks:
            best = max(scored_tasks, key=scored_tasks.__getitem__)
            task = self._make_task(
                best,
                food_target,
                water_target,
                explore_target,
                thirst_explore_target,
                rest_target,
            )
            return task

        if not is_idle and active_task_name:
            need_name = task_to_need_map.get(active_task_name, "")
            need_urgency = urgency_map.get(need_name, 0.0)

            task_targets = {
                "seek_food": food_target,
                "seek_water": water_target,
                "seek_rest": rest_target,
                "harvest_food": local_plant,
            }
            valid_target = (
                active_task_name not in task_targets
                or task_targets[active_task_name] is not None
            )

            if need_urgency >= idle_threshold and valid_target:
                task = self._make_task(
                    active_task_name,
                    food_target,
                    water_target,
                    explore_target,
                    thirst_explore_target,
                    rest_target,
                )
                return task

        if mate_pos:
            return Task(priority=0, name="mate", goal_pos=mate_pos)

        return Task(priority=0, name="explore", goal_pos=explore_target)

    def _make_task(
        self,
        active_task: str,
        food: Pos | None,
        water: Pos | None,
        explore: Pos,
        thirst_explore: Pos,
        rest_target: Pos | None,
    ) -> Task:
        goal: Pos | None = {
            "seek_food": food,
            "seek_water": water,
            "explore": explore,
            "thirst_explore": thirst_explore,
            "seek_rest": rest_target,
        }.get(active_task)

        return Task(priority=0, name=active_task, goal_pos=goal or explore)

    def plan_steps(
        self,
        mate_pos: Pos | None,
        at_river_tile: bool,
        local_plant: Plant | None,
        world: World,
        valid_moves: list[Pos],
        occupied_tiles: set[Pos] | None,
        tick_count: int,
    ) -> None:
        priority_task = self.choose_action(
            mate_pos=mate_pos,
            at_river_tile=at_river_tile,
            local_plant=local_plant,
            occupied_tiles=occupied_tiles,
        )

        if priority_task.name == "drink":
            self.needs.is_drinking = True

        if priority_task.name == "harvest_food" and self.needs.harvest_count == 0:
            self.needs.harvest_count = local_plant.ticks_per_fruit
            event_bus.publish(
                Event(
                    "harvest_started",
                    {
                        "agent_id": str(self.id),
                        "plant_id": str(local_plant.id),
                    },
                )
            )

        if priority_task.name == "sleep":
            self.needs.is_sleeping = True

        if priority_task.goal_pos == self.pos:
            self.active_task = priority_task
            self.planned_steps = [self.pos]
            self.next_decision_tick = tick_count + 1
            return

        if self.needs_replan(priority_task):
            self.path = astar(world, self.pos, priority_task.goal_pos, occupied_tiles)

        if not self.path:
            self.active_task = Task(
                priority=0, name="explore", goal_pos=self.get_explore_goal()
            )
            self.path = astar(world, self.pos, self.active_task.goal_pos)

            if not self.path:
                self.planned_steps = [self.pos]
                self.next_decision_tick = tick_count + 1
                return

        self.active_task = priority_task

        step = self.path[0]

        if step not in valid_moves and step != priority_task.goal_pos:
            self.planned_steps = [self.pos]
            self.next_decision_tick = tick_count + 1
            return

        self.path.pop(0)

        steps = [step]

        if self.path:
            steps.append(self.path[0])

        self.planned_steps = steps
        self.next_decision_tick = tick_count + len(steps)

    def tick_movement(
        self,
        is_river_tile: Callable[[Pos], bool],
        occupied: set[Pos],
        tick_count: int,
        elevation_at: Callable[[Pos], float],
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

                if self.needs.is_sleeping:
                    self.planned_steps.clear()
                elif self.pos != old_pos:
                    elev_gain = elevation_at(self.pos) - elevation_at(old_pos)

                    if elev_gain > 0:
                        self.needs.drain_uphill(elev_gain)

        occupied.discard(old_pos)
        occupied.add(self.pos)
        self.age += 1

        self.needs.apply_rest_drain(temperature)
        self.needs.apply_hunger_drain(self.age, is_river_tile(self.pos))
        self.needs.apply_thirst_drain()

        event_bus.publish(Event("agent_moved", {"agent": self.model_dump(mode="json")}))

    def get_explore_goal(self) -> Pos:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(15, 25)
        return Pos(
            max(0, min(WORLD_WIDTH - 1, int(self.x + dist * math.cos(angle)))),
            max(0, min(WORLD_HEIGHT - 1, int(self.y + dist * math.sin(angle)))),
        )

    def get_thirst_explore_goal(self) -> Pos:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(40, 70)
        return Pos(
            max(0, min(WORLD_WIDTH - 1, int(self.x + dist * math.cos(angle)))),
            max(0, min(WORLD_HEIGHT - 1, int(self.y + dist * math.sin(angle)))),
        )
