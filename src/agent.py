import heapq
import math
import random
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from food import Food
from tasks import Task, PRIORITY_EXPLORE, PRIORITY_MATE, PRIORITY_RETURN_HOME, PRIORITY_SEEK_FOOD, PRIORITY_SEEK_FOOD_SATED

MAX_HEALTH = 80
MAX_REST = 80
REST_THRESHOLD_DEFAULT = 40
NIGHT_DRAIN_DEFAULT = 3
VISION_RANGE = 20
REST_DRAIN = 1
REST_RESTORE = 3
REPRODUCTION_MATURITY_AGE = 30
REPRODUCTION_HEALTH_THRESHOLD = 0.87
ADULT_DRAIN = 3
INFANT_DRAIN = 3
MATURITY_AGE = 30
WATER_DRAIN_MULTIPLIER = 2
LONE_HEALTH_PENALTY = 1
DEFAULT_HEALTH_OVERRIDE = 60


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    health: int = MAX_HEALTH
    vision_range: int = VISION_RANGE
    group_id: UUID | None = None
    age: int = 0
    alive: bool = True
    direction: tuple[int, int] | None = None
    last_food_seen: tuple[int, int] | None = None
    birth_tick: int = 0
    mutations: list[str] = Field(default_factory=list)
    genotype: dict[str, int] = Field(default_factory=dict)
    metabolism: float = 1.0
    is_adult: bool = False

    rest: int = MAX_REST
    rest_threshold: int = REST_THRESHOLD_DEFAULT
    night_drain: int = NIGHT_DRAIN_DEFAULT
    is_sleeping: bool = False
    health_override: int = DEFAULT_HEALTH_OVERRIDE
    home_pos: tuple[int, int] | None = None
    carried_food: Food | None = None
    active_task: Task | None = None
    path: list[tuple[int, int]] = Field(default_factory=list)

    def move_to(self, x: int, y: int) -> None:
        self.direction = (x - self.x, y - self.y)
        self.x = x
        self.y = y

    def eat(self) -> None:
        self.health = MAX_HEALTH
        self.direction = None

    def drain_health(self, amount: int) -> None:
        self.health -= amount

    def die(self) -> None:
        self.alive = False
        self.active_task = None
        self.path = []

    def see_food(self, pos: tuple[int, int]) -> None:
        self.last_food_seen = pos

    def forget_food(self) -> None:
        self.last_food_seen = None

    def starvation_drain(self) -> int:
        if self.is_adult:
            return ADULT_DRAIN
        t = min(self.age, MATURITY_AGE) / MATURITY_AGE
        return max(1, round(INFANT_DRAIN + (1 - INFANT_DRAIN) * t))

    def should_rest(self) -> bool:
        return self.is_sleeping and self.health > self.health_override

    def apply_hunger_drain(self, is_river: bool, is_lone: bool) -> None:
        base = round(self.starvation_drain() * self.metabolism)
        water = base * (WATER_DRAIN_MULTIPLIER - 1) if is_river else 0
        lone = LONE_HEALTH_PENALTY if is_lone else 0
        self.drain_health(base + water + lone)

    def update_food_memory(self, food_targets: list[Food]) -> None:
        if food_targets:
            nearest = min(food_targets, key=lambda f: abs(f.x - self.x) + abs(f.y - self.y))
            self.see_food((nearest.x, nearest.y))
        elif self.last_food_seen:
            mx, my = self.last_food_seen
            if abs(self.x - mx) + abs(self.y - my) <= 2:
                self.forget_food()

    def tick_rest(self, is_night: bool) -> None:
        if self.is_sleeping:
            self.rest = min(MAX_REST, self.rest + REST_RESTORE)
        elif is_night:
            self.rest = max(0, self.rest - self.night_drain)
        else:
            self.rest = max(0, self.rest - REST_DRAIN)

        if not self.is_sleeping and self.rest <= self.rest_threshold:
            self.is_sleeping = True
        elif self.is_sleeping and self.rest >= MAX_REST:
            self.is_sleeping = False

    def explore_goal(self, world_width: int, world_height: int) -> tuple[int, int]:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(10, 25)
        ex = max(0, min(world_width - 1, int(self.x + dist * math.cos(angle))))
        ey = max(0, min(world_height - 1, int(self.y + dist * math.sin(angle))))
        return (ex, ey)

    def is_eligible_to_mate(self) -> bool:
        return (
            self.age >= REPRODUCTION_MATURITY_AGE
            and self.health >= int(MAX_HEALTH * REPRODUCTION_HEALTH_THRESHOLD)
            and not self.is_sleeping
        )

    def build_task_queue(
        self,
        food_targets: list[Food],
        mate_pos: tuple[int, int] | None,
        explore_goal: tuple[int, int],
        food_goal_still_valid: bool = False,
    ) -> list[Task]:
        queue: list[Task] = []

        desperate = self.health < MAX_HEALTH * 0.5

        if self.carried_food is not None and self.home_pos is not None:
            heapq.heappush(queue, Task(PRIORITY_RETURN_HOME, "return_home", self.home_pos))
        else:
            if food_targets:
                nearest = min(food_targets, key=lambda f: abs(f.x - self.x) + abs(f.y - self.y))
                food_goal = (nearest.x, nearest.y)
                if self.active_task and self.active_task.name == "seek_food":
                    curr_dist = abs(self.x - self.active_task.goal_pos[0]) + abs(self.y - self.active_task.goal_pos[1])
                    new_dist = abs(nearest.x - self.x) + abs(nearest.y - self.y)
                    if new_dist >= curr_dist - 3 and food_goal_still_valid:
                        food_goal = self.active_task.goal_pos
                sated = not desperate and self.health >= MAX_HEALTH * 0.8
                food_priority = PRIORITY_SEEK_FOOD_SATED if sated else PRIORITY_SEEK_FOOD
                heapq.heappush(queue, Task(food_priority, "seek_food", food_goal))
            elif self.last_food_seen:
                sated = not desperate and self.health >= MAX_HEALTH * 0.8
                food_priority = PRIORITY_SEEK_FOOD_SATED if sated else PRIORITY_SEEK_FOOD
                heapq.heappush(queue, Task(food_priority, "seek_food", self.last_food_seen))

            if mate_pos and not desperate:
                heapq.heappush(queue, Task(PRIORITY_MATE, "mate", mate_pos))

        if self.active_task and self.active_task.name == "explore" and self.path:
            explore_goal = self.active_task.goal_pos
        heapq.heappush(queue, Task(PRIORITY_EXPLORE, "explore", explore_goal))

        return queue
