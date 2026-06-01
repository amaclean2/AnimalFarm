import math

from pydantic import BaseModel

from config import MEMORY_CAP, CONFIDENCE_PRUNE, DECAY_RATE, FAMILIARITY_WEIGHT
from pos import Pos


class MemoryEntry(BaseModel):
    pos: Pos
    quality: float
    added_tick: int
    visit_count: int = 1
    decay_rate: float = DECAY_RATE

    def confidence(self, tick: int) -> float:
        return max(0.0, 1.0 - (tick - self.added_tick) * self.decay_rate)

    def score(self, tick: int, familiarity: bool = False) -> float:
        base = self.quality * self.confidence(tick)
        if familiarity and self.visit_count > 1:
            base *= 1.0 + FAMILIARITY_WEIGHT * math.log1p(self.visit_count - 1)
        return base


class Memory(BaseModel):
    food: list[MemoryEntry] = []
    water: list[MemoryEntry] = []
    rest: list[MemoryEntry] = []

    def observe(self, pos: Pos, kind: str, quality: float, tick: int) -> None:
        entries = self._bucket(kind)

        for entry in entries:
            if entry.pos == pos:
                entry.quality = quality
                entry.added_tick = tick
                entry.visit_count += 1
                return

        entries.append(MemoryEntry(pos=pos, quality=quality, added_tick=tick))

        if len(entries) > MEMORY_CAP:
            entries.sort(key=lambda e: e.quality, reverse=True)
            del entries[MEMORY_CAP:]

    def query(
        self, kind: str, tick: int, urgency: float = 0.0, familiarity: bool = False
    ) -> Pos | None:

        entries = [
            e for e in self._bucket(kind) if e.confidence(tick) >= CONFIDENCE_PRUNE
        ]
        self._set_bucket(kind, entries)

        if not entries:
            return None

        return max(entries, key=lambda e: e.score(tick, familiarity=familiarity)).pos

    def best_score(self, kind: str, tick: int, familiarity: bool = False) -> float:
        entries = [
            entry
            for entry in self._bucket(kind)
            if entry.confidence(tick) >= CONFIDENCE_PRUNE
        ]
        if not entries:
            return 0.0
        return max(entry.score(tick, familiarity=familiarity) for entry in entries)

    def quality_of(self, kind: str, pos: Pos) -> float:
        for entry in self._bucket(kind):
            if entry.pos == pos:
                return entry.quality
        return 0.0

    def _bucket(self, kind: str) -> list[MemoryEntry]:
        return {
            "food": self.food,
            "water": self.water,
            "rest": self.rest,
        }[kind]

    def _set_bucket(self, kind: str, entries: list[MemoryEntry]) -> None:
        match kind:
            case "food":
                self.food = entries
            case "water":
                self.water = entries
            case "rest":
                self.rest = entries
