from pydantic import BaseModel

from config import MEMORY_CAP
from pos import Pos


class Memory(BaseModel):
    food: list[Pos] = []
    water: list[Pos] = []
    rest: list[Pos] = []

    def observe(self, pos: Pos, kind: str, agent_pos: Pos) -> None:
        entries = self._bucket(kind)

        if pos in entries:
            return

        entries.append(pos)

        if len(entries) > MEMORY_CAP:
            furthest = max(
                entries, key=lambda p: abs(p.x - agent_pos.x) + abs(p.y - agent_pos.y)
            )
            entries.remove(furthest)

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
