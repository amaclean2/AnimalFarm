import math
import random
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from agents.memory import Memory
from agents.needs import NeedState
import config as _cfg
from config import (
    REPRODUCTION_HUNGER_THRESHOLD,
    MATING_COOLDOWN,
    VISION_RANGE,
    CONTINUATION_BONUS,
    HARVEST_CONTINUATION_BONUS,
    WATER_URGENCY_DISTANCE_SCALE,
    WATER_LOST_URGENCY_MULTIPLIER,
)
from pos import Pos
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
    "thirst_explore": {
        "hunger": 0.0,
        "thirst": 1.0,
        "rest": -0.3,
        "safety": -0.3,
        "social": -0.1,
        "reproduction": 0.0,
        "curiosity": 0.0,
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

    carried_food: int = 0

    harvest_target: UUID | None = None
    harvest_ticks: int = 0

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

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)

    @property
    def last_food_seen(self) -> Pos | None:
        if not self.memory.food:
            return None
        return max(self.memory.food, key=lambda e: e.added_tick).pos

    # --- lifecycle ---

    def move_to(self, pos: Pos) -> None:
        self.direction = (pos.x - self.x, pos.y - self.y)
        self.x = pos.x
        self.y = pos.y

    def eat(self) -> None:
        self.needs.eat()
        self.direction = None

    def drink(self) -> None:
        self.needs.drink()

    def die(self) -> None:
        self.alive = False
        self.active_task = None
        self.path = []
        self.planned_steps = []
        self.harvest_target = None
        self.harvest_ticks = 0

    def should_die(self) -> bool:
        return (
            self.hunger <= 0
            or self.needs.water <= 0
            or self.needs.rest <= 0
            or self.age >= _cfg.MAX_AGE
        )

    def continue_sleeping(self) -> bool:
        """If already sleeping and still needs rest, keep sleeping and return True.
        Resets is_sleeping to False otherwise so try_fall_asleep can set it cleanly."""
        was = self.needs.is_sleeping
        self.needs.is_sleeping = False

        if was and self.needs.rest < 1.0:
            self.needs.is_sleeping = True
            return True

        return False

    def try_fall_asleep(self, at_rest_target: bool, is_river: bool = False) -> bool:
        """Transition to sleeping if the current task calls for it. Returns True if now sleeping."""
        if (
            self.active_task
            and self.active_task.name == "sleep"
            and at_rest_target
            and not is_river
        ):
            self.needs.is_sleeping = True
            return True

        return False

    # --- need delegation ---

    def tick_needs(
        self, is_night: bool, tile_quality: float = 1.0, temperature: float = 0.5
    ) -> None:
        self.needs.tick(is_night, tile_quality, temperature)

    def apply_hunger_drain(self, is_river: bool) -> None:
        self.needs.apply_hunger_drain(self.age, self.is_adult, is_river)

    def drain_uphill(self, elev_gain: float) -> None:
        self.needs.drain_uphill(elev_gain)

    # --- memory delegation ---

    def update_food_memory(self, plant_targets: list, tick: int) -> None:
        for plant in plant_targets:
            self.memory.observe(plant.pos, "food", 1.0, tick)

    def update_water_memory(self, visible_water: list[Pos], tick: int) -> None:
        for pos in visible_water:
            self.memory.observe(pos, "water", 1.0, tick)

    def update_rest_memory(self, pos: Pos, quality: float, tick: int) -> None:
        self.memory.observe(pos, "rest", quality, tick)

    def update_rest_target(
        self,
        visible_rest: Pos | None,
        visible_q: float,
        sleeping_tiles: set[Pos],
        is_night: bool,
        tick: int,
    ) -> None:
        if self.needs.rest >= 0.8:
            self.rest_target = None
            return

        drain_rate = _cfg.REST_BASE_DRAIN * (
            _cfg.REST_NIGHT_MULTIPLIER if is_night else 1.0
        )
        usable = max(0.0, self.needs.rest - _cfg.REST_SAFETY_BUFFER_FRAC)
        max_travel = max(1, int(usable / drain_rate))

        if self.rest_target is not None:
            cur_dist = abs(self.x - self.rest_target.x) + abs(
                self.y - self.rest_target.y
            )
            if self.rest_target in sleeping_tiles or cur_dist > max_travel:
                self.rest_target = None

        if self.rest_target is None:
            memory_rest = self.memory.query("rest", tick, familiarity=True)

            if memory_rest is not None:
                mem_dist = abs(self.x - memory_rest.x) + abs(self.y - memory_rest.y)
                if mem_dist > max_travel or memory_rest in sleeping_tiles:
                    memory_rest = None

            if visible_rest and memory_rest:
                mem_q = self.memory.quality_of("rest", memory_rest)
                mem_dist = abs(self.x - memory_rest.x) + abs(self.y - memory_rest.y)
                decay = max(0.0, 1.0 - mem_dist / max(max_travel, 1))
                mem_score = mem_q + _cfg.MEMORY_REST_BONUS * decay
                self.rest_target = (
                    memory_rest if mem_score >= visible_q else visible_rest
                )
            elif visible_rest:
                self.rest_target = visible_rest
            elif memory_rest:
                self.rest_target = memory_rest
        elif visible_rest:
            vis_dist = abs(self.x - visible_rest.x) + abs(self.y - visible_rest.y)
            cur_dist = abs(self.x - self.rest_target.x) + abs(
                self.y - self.rest_target.y
            )
            if vis_dist < cur_dist * 0.7:
                self.rest_target = visible_rest

    # --- reproduction ---

    def is_eligible_to_mate(self, tick: int) -> bool:
        return (
            self.age >= _cfg.MATURITY_AGE
            and self.needs.hunger >= REPRODUCTION_HUNGER_THRESHOLD
            and not self.needs.is_sleeping
            and tick - self.last_mated_tick >= MATING_COOLDOWN
        )

    # --- decision making ---

    def choose_action(
        self,
        is_night: bool,
        mate_pos: Pos | None,
        explore_goal: Pos,
        thirst_explore_goal: Pos,
        tick: int,
        rest_target: Pos | None = None,
        harvesting: bool = False,
    ) -> Task:
        urgencies = self.needs.urgency_vector()
        food_target = self.memory.query("food", tick, urgency=urgencies["hunger"])
        water_target = self.memory.query("water", tick, urgency=urgencies["thirst"])

        if water_target:
            dist = abs(water_target.x - self.x) + abs(water_target.y - self.y)
            # Knowing where water is brings comfort — urgency scales down when nearby,
            # approaching normal as distance grows. Floor prevents comfort from
            # overriding critical thirst: a 90%-depleted agent keeps 90% of raw urgency.
            comfort = 0.2 + 0.8 * dist / (dist + WATER_URGENCY_DISTANCE_SCALE)
            urgencies["thirst"] = max(
                urgencies["thirst"] * comfort,
                urgencies["thirst"] * (1.0 - self.needs.water),
            )
        else:
            # No perception of water — amplify urgency; hunger capped so thirst_explore wins
            urgencies["thirst"] = min(
                1.0, urgencies["thirst"] * WATER_LOST_URGENCY_MULTIPLIER
            )
            urgencies["hunger"] = min(urgencies["hunger"], urgencies["thirst"] * 0.5)

        candidates = self._feasible_actions(
            food_target, water_target, mate_pos, rest_target
        )

        best_action, best_score = "explore", float("-inf")

        for action in candidates:
            score = sum(urgencies[need] * _RELEVANCE[action][need] for need in _NEEDS)

            if self.active_task and self.active_task.name == action:
                score += CONTINUATION_BONUS
                if harvesting and action == "seek_food":
                    score += HARVEST_CONTINUATION_BONUS

            if score > best_score:
                best_score, best_action = score, action

        return self._resolve_task(
            best_action,
            food_target,
            water_target,
            mate_pos,
            explore_goal,
            thirst_explore_goal,
            rest_target,
        )

    def _feasible_actions(
        self,
        food_target: Pos | None,
        water_target: Pos | None,
        mate_pos: Pos | None,
        rest_target: Pos | None = None,
    ) -> list[str]:
        if self.needs.is_sleeping and self.needs.rest < 1.0 and rest_target:
            return ["sleep"]

        actions = ["explore"]

        if food_target:
            actions.append("seek_food")

        if water_target:
            actions.append("drink")
        else:
            actions.append("thirst_explore")

        if self.needs.rest < 1.0 and (
            rest_target or self.needs.rest <= _cfg.REST_SAFETY_BUFFER_FRAC * 2
        ):
            actions.append("sleep")

        if mate_pos:
            actions.append("mate")

        return actions

    def _resolve_task(
        self,
        action: str,
        food: Pos | None,
        water: Pos | None,
        mate: Pos | None,
        explore: Pos,
        thirst_explore: Pos,
        rest: Pos | None = None,
    ) -> Task:
        if action == "sleep":
            return Task(priority=0, name="sleep", goal_pos=rest or self.pos)
        goal: Pos | None = {
            "seek_food": food,
            "drink": water,
            "mate": mate,
            "explore": explore,
            "thirst_explore": thirst_explore,
        }.get(action, explore)
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
