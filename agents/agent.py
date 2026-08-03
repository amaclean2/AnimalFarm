import math
import random
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from agents.inventory import Inventory
from agents.memory import Memory
from agents.needs import NeedState
from agents.scoring import ScoringContext, choose_best
import deps
import event_bus
from events import Event
from config import (
    MATING_COOLDOWN,
    MAX_AGE,
    MATURITY_AGE,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    IDEAL_CORE_TEMP_C,
    CORE_TEMP_DEATH_MARGIN_C,
)
from genome import GENE_DEFAULTS, default_genome
from pathfinding import astar
from plant import Plant
from pos import Pos
from tasks import Task
from world import World


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    age: int = 0
    alive: bool = True
    birth_tick: int = 0
    vision_range: int = round(GENE_DEFAULTS["vision"])

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
    inventory: Inventory = Field(default_factory=Inventory)
    fruits_harvested: int = 0

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

    def die(self, sim_id: str, tick_count: int) -> None:
        genome_pool = getattr(deps, "genome_pool", None)

        if genome_pool is not None:
            genome_pool.record(self, sim_id, tick_count)

        self.alive = False
        self.active_task = Task(priority=100, name="explore", goal_pos=self.pos)
        self.path = []
        self.planned_steps = []
        self.needs.stop_harvest()
        self.needs.is_drinking = False
        self.needs.is_eating = False

        event_bus.publish(Event("agent_died", {"agent": self.model_dump(mode="json")}))

    def should_die(self) -> bool:
        return (
            self.needs.hunger >= 1.0
            or self.needs.water >= 1.0
            or self.needs.rest >= 1.0
            or self.age >= MAX_AGE
            or abs(self.needs.core_temperature - IDEAL_CORE_TEMP_C)
            >= CORE_TEMP_DEATH_MARGIN_C
        )

    def needs_replan(self, priority_task: Task) -> bool:
        return (
            priority_task.name != self.active_task.name
            or priority_task.goal_pos != self.active_task.goal_pos
            or not self.path
        )

    def sleep(self, tile_quality: float = 1.0) -> None:
        self.age += 1
        self.needs.sleep(tile_quality)
        event_bus.publish(
            Event("agent_sleeping", {"agent": self.model_dump(mode="json")})
        )

    @property
    def harvest_skill(self) -> float:
        return math.log2(self.fruits_harvested + 1) / 4 + 1

    def harvest(self) -> None:
        self.age += 1
        self.needs.apply_thirst_drain(self.age)
        self.needs.harvest(self.harvest_skill)

        if self.needs.is_harvesting:
            return

        self.inventory.add("fruit", 1.0)
        self.fruits_harvested += 1

    def eat(self) -> None:
        self.age += 1
        taken = self.inventory.take("fruit", 1.0)

        if taken > 0.0:
            self.needs.eat()
        else:
            self.needs.is_eating = False

        event_bus.publish(Event("agent_ate", {"agent": self.model_dump(mode="json")}))

    def drink(self) -> None:
        self.age += 1
        self.needs.drink()
        event_bus.publish(Event("agent_drank", {"agent_id": str(self.id)}))

    def update_memory(self, snapshot: "VisionSnapshot") -> None:
        for plant in snapshot.food_targets:
            self.memory.observe(
                plant.pos,
                "food",
                self.pos,
                fruit_count=plant.fruit_count,
                crowd=snapshot.food_crowd.get(plant.pos, 0),
            )

        for water in snapshot.visible_water:
            self.memory.observe(water, "water", self.pos)

        if snapshot.visible_rest is not None:
            self.memory.observe(snapshot.visible_rest, "rest", self.pos)

    def is_eligible_to_mate(self, tick_count: int) -> bool:
        return (
            self.age >= MATURITY_AGE
            and not self.needs.is_sleeping
            and (tick_count - self.last_mated_tick) >= MATING_COOLDOWN
        )

    def choose_action(
        self,
        mate_pos: Pos | None,
        at_river_tile: bool = False,
        local_plant: Plant | None = None,
        occupied_tiles: set[Pos] | None = None,
        world: World | None = None,
    ) -> Task:
        context = ScoringContext(
            world=world,
            mate_pos=mate_pos,
            at_river_tile=at_river_tile,
            local_plant=local_plant,
            occupied_tiles=occupied_tiles,
        )
        best = choose_best(self, context)
        return Task(priority=0, name=best.task_name, goal_pos=best.goal_pos)

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
            world=world,
        )

        if priority_task.name == "drink":
            self.needs.is_drinking = True

        if priority_task.name == "eat":
            self.needs.is_eating = True

        if priority_task.name == "harvest_food" and not self.needs.is_harvesting:
            self.needs.start_harvest(
                local_plant.fruit_per_tick, local_plant.eat_restore
            )
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

        self.needs.apply_rest_drain(self.age)
        self.needs.apply_hunger_drain(self.age, is_river_tile(self.pos))
        self.needs.apply_thirst_drain(self.age)
        self.needs.apply_temperature_drift(temperature)

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
