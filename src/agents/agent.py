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
    REPRODUCTION_HUNGER_THRESHOLD,
    VISION_RANGE,
    WATER_BASE_DRAIN,
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
    is_adult: bool = False
    birth_tick: int = 0
    vision_range: int = VISION_RANGE

    genotype: dict[str, int] = Field(default_factory=dict)
    mutations: list[str] = Field(default_factory=list)
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
        if not self.memory.food:
            return None
        return max(self.memory.food, key=lambda e: e.added_tick).pos

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

    def apply_rest_drain(self, temperature: float = 15.0) -> None:
        self.needs.apply_rest_drain(temperature)

    def sleep(self, tile_quality: float = 1.0) -> bool:
        self.age += 1
        sleeping_complete = self.needs.sleep(tile_quality)
        event_bus.publish(
            Event("agent_sleeping", {"agent": self.model_dump(mode="json")})
        )

        if sleeping_complete:
            return True

        return False

    def apply_hunger_drain(self, is_river: bool) -> None:
        self.needs.apply_hunger_drain(self.age, self.is_adult, is_river)

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

    def update_memory(
        self,
        food_targets: list,
        visible_water: list[Pos],
        visible_rest: Pos | None,
        tick: int,
    ) -> None:
        for plant in food_targets:
            self.memory.observe(plant.pos, "food", 1.0, tick)

        for pos in visible_water:
            self.memory.observe(pos, "water", 1.0, tick)

        if visible_rest is not None:
            self.memory.observe(visible_rest, "rest", 1.0, tick)

    def is_eligible_to_mate(self, tick: int) -> bool:
        return (
            self.age >= MATURITY_AGE
            and self.needs.hunger >= REPRODUCTION_HUNGER_THRESHOLD
            and not self.needs.is_sleeping
            and tick - self.last_mated_tick >= MATING_COOLDOWN
        )

    def calculate_urgencies(self):
        water_resources = self.memory.water
        closest_water_resource = (
            min(
                water_resources,
                key=lambda e: abs(e.pos.x - self.x) + abs(e.pos.y - self.y),
            )
            if water_resources
            else None
        )
        closest_water_resource_dist = (
            abs(closest_water_resource.pos.x - self.x)
            + abs(closest_water_resource.pos.y - self.y)
            if closest_water_resource is not None
            else None
        )
        thirst_ticks_to_empty = self.needs.water / WATER_BASE_DRAIN

        thirst_urgency = (1.0 - self.needs.water) ** 2

        if (
            closest_water_resource_dist is not None
            and closest_water_resource_dist + 2 >= thirst_ticks_to_empty
        ):
            thirst_urgency = 1.0

        return {
            "thirst": thirst_urgency,
            "hunger": (1.0 - self.needs.hunger) ** 2,
            "rest": (1.0 - self.needs.rest) ** 2,
        }

    def choose_action(
        self,
        mate_pos: Pos | None,
        tick: int,
        at_river_tile: bool = False,
        local_plant: Plant | None = None,
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

        food_target = self.memory.query("food", tick, pos=self.pos)
        water_target = self.memory.query("water", tick, pos=self.pos)
        rest_target = self.memory.query("rest", tick, pos=self.pos)

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

        if mate_pos and self.is_eligible_to_mate(tick):
            print(mate_pos)
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
            tick=tick_count,
            at_river_tile=at_river_tile,
            local_plant=local_plant,
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

        self.active_task = priority_task

        first_step = None

        step = self.path[0]

        if step in valid_moves or step == priority_task.goal_pos:
            self.path.pop(0)
            first_step = step
        else:
            self.path = astar(
                world,
                self.pos,
                priority_task.goal_pos,
                occupied_tiles,
            )

            if self.path[0] in valid_moves or self.path[0] == priority_task.goal_pos:
                first_step = self.path.pop(0)

        steps = [first_step]

        if first_step != self.pos and self.path:
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

        self.apply_rest_drain(temperature)
        self.apply_hunger_drain(is_river_tile(self.pos))
        self.apply_thirst_drain()

        event_bus.publish(Event("agent_moved", {"agent": self.model_dump(mode="json")}))

    def get_explore_goal(self) -> Pos:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(15, 35)
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
