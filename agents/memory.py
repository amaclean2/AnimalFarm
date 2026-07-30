from pydantic import BaseModel

from config import MEMORY_CAP
from pos import Pos


class FoodInfo(BaseModel):
    fruit_count: float
    crowd: int


class Memory(BaseModel):
    food: list[Pos] = []
    water: list[Pos] = []
    rest: list[Pos] = []
    food_info: dict[Pos, FoodInfo] = {}

    def observe(
        self,
        pos: Pos,
        kind: str,
        agent_pos: Pos,
        fruit_count: float | None = None,
        crowd: int | None = None,
    ) -> None:
        entries = self._bucket(kind)

        if pos not in entries:
            entries.append(pos)

            if len(entries) > MEMORY_CAP:
                furthest = max(
                    entries,
                    key=lambda p: abs(p.x - agent_pos.x) + abs(p.y - agent_pos.y),
                )
                entries.remove(furthest)

                if kind == "food":
                    self.food_info.pop(furthest, None)

        if kind == "food" and pos in entries:
            self.food_info[pos] = FoodInfo(fruit_count=fruit_count, crowd=crowd)

    def pick_best_food(
        self, agent_pos: Pos, harvest_skill: float, exclude: set[Pos] | None = None
    ) -> Pos | None:
        entries = [entry for entry in self.food if not exclude or entry not in exclude]

        if not entries:
            return None

        def score(food_pos: Pos) -> float:
            info = self.food_info[food_pos]
            distance = abs(food_pos.x - agent_pos.x) + abs(food_pos.y - agent_pos.y)
            return -distance + harvest_skill * (info.fruit_count - info.crowd)

        return max(entries, key=score)

    def forget(self, pos: Pos, kind: str) -> None:
        entries = self._bucket(kind)

        if pos in entries:
            entries.remove(pos)

            if kind == "food":
                self.food_info.pop(pos, None)

    def query(
        self,
        kind: str,
        pos: Pos,
        max_dist: int | None = None,
        exclude: set[Pos] | None = None,
    ) -> Pos | None:
        entries = self._bucket(kind)

        if not entries:
            return None

        if max_dist is not None:
            entries = [
                e for e in entries if abs(e.x - pos.x) + abs(e.y - pos.y) <= max_dist
            ]

            if not entries:
                return None

        if exclude:
            entries = [e for e in entries if e not in exclude]

            if not entries:
                return None

        return min(entries, key=lambda e: abs(e.x - pos.x) + abs(e.y - pos.y))

    def _bucket(self, kind: str) -> list[Pos]:
        return {
            "food": self.food,
            "water": self.water,
            "rest": self.rest,
        }[kind]
