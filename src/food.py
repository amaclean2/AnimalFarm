import random
from collections import defaultdict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from config import (
    FOOD_CLUSTER_WEIGHT,
    FOOD_REGROW_TICKS,
    FOOD_SCORE_FLOOR,
    FOOD_SPREAD_CANDIDATES,
    FOOD_SPREAD_SIGMA,
    FOOD_WATER_WEIGHT,
)
from pos import Pos


class FoodItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    value: int = 1

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)


class FoodManager:
    def __init__(self, world) -> None:
        self._world = world
        self._food: dict[Pos, FoodItem] = {}
        self._regrow_queue: dict[int, list[Pos]] = defaultdict(list)

    def schedule_regrow(self, pos: Pos, current_tick: int) -> None:
        self._regrow_queue[current_tick + FOOD_REGROW_TICKS].append(pos)

    def process_regrow(self, tick: int, events: list[tuple[str, dict]]) -> None:
        for pos in self._regrow_queue.pop(tick, []):
            if (
                not self._world.rivers.is_river_tile(pos)
                and self.get_food_at(pos) is None
            ):
                food = self.place_food(pos)
                events.append(("food_grew", {"food": food.model_dump(mode="json")}))

    def place_food(self, pos: Pos, value: int = 1) -> FoodItem:
        if not self._world.in_bounds(pos):
            raise ValueError(f"Position {pos} is out of bounds")
        if pos in self._food:
            raise ValueError(f"FoodItem already exists at {pos}")
        food = FoodItem(x=pos.x, y=pos.y, value=value)
        self._food[pos] = food
        return food

    def get_food_at(self, pos: Pos) -> FoodItem | None:
        return self._food.get(pos)

    def get_food(self, food_id: UUID) -> FoodItem | None:
        return next((f for f in self._food.values() if f.id == food_id), None)

    def remove_food(self, food_id: UUID) -> FoodItem | None:
        food = self.get_food(food_id)
        if food:
            del self._food[food.pos]
        return food

    def remove_food_at(self, pos: Pos) -> FoodItem | None:
        return self._food.pop(pos, None)

    @property
    def all_food(self) -> list[FoodItem]:
        return list(self._food.values())

    def food_in_vision(
        self, agent, vision_range: float | None = None
    ) -> list[FoodItem]:
        r = vision_range if vision_range is not None else agent.vision_range
        return [
            f
            for f in self._food.values()
            if abs(f.x - agent.x) + abs(f.y - agent.y) <= r
        ]

    def compute_food_visibility(self, agent_vision: dict, agents) -> dict:
        group_shared_food: dict[UUID, list[FoodItem]] = {}
        for group in agents.all_groups:
            seen_ids: set[UUID] = set()
            shared: list[FoodItem] = []
            for mid in group.member_ids:
                member = agents.get(mid)
                if not member:
                    continue
                for f in self.food_in_vision(member, agent_vision[mid]):
                    if f.id not in seen_ids:
                        seen_ids.add(f.id)
                        shared.append(f)
            group_shared_food[group.id] = shared

        agent_food: dict[UUID, list[FoodItem]] = {}
        for agent in agents.all_living:
            group = agents.group_for_agent(agent.id)
            agent_food[agent.id] = (
                group_shared_food[group.id]
                if group
                else self.food_in_vision(agent, agent_vision[agent.id])
            )
        return agent_food

    def spawn_food_near(self, anchor: Pos, events: list[tuple[str, dict]]) -> None:
        river_tiles = list(self._world.rivers.all_tiles)
        food_list = self.all_food

        candidates: list[Pos] = []
        for _ in range(FOOD_SPREAD_CANDIDATES):
            p = Pos(
                int(random.gauss(anchor.x, FOOD_SPREAD_SIGMA)),
                int(random.gauss(anchor.y, FOOD_SPREAD_SIGMA)),
            )
            if not self._world.in_bounds(p):
                continue
            if self._world.rivers.is_river_tile(p):
                continue
            if self.get_food_at(p) is not None:
                continue
            candidates.append(p)

        if not candidates:
            return

        weights: list[float] = []
        for p in candidates:
            if river_tiles:
                water_dist = min(abs(p.x - r.x) + abs(p.y - r.y) for r in river_tiles)
                water_score = FOOD_WATER_WEIGHT / (1 + water_dist)
            else:
                water_score = 0.0

            if food_list:
                cluster_dist = min(abs(p.x - f.x) + abs(p.y - f.y) for f in food_list)
                cluster_score = FOOD_CLUSTER_WEIGHT / (1 + cluster_dist)
            else:
                cluster_score = 0.0

            weights.append(water_score + cluster_score + FOOD_SCORE_FLOOR)

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        food = FoodItem(x=chosen.x, y=chosen.y)
        self._food[chosen] = food
        events.append(("food_grew", {"food": food.model_dump(mode="json")}))

    def reset(self) -> None:
        self._food.clear()
        self._regrow_queue.clear()
