from pydantic import BaseModel

from config import MEMORY_CAP, CONFIDENCE_PRUNE, DECAY_RATE


class MemoryEntry(BaseModel):
    pos: tuple[int, int]
    quality: float
    added_tick: int
    visit_count: int = 1
    decay_rate: float = DECAY_RATE

    def confidence(self, tick: int) -> float:
        return max(0.0, 1.0 - (tick - self.added_tick) * self.decay_rate)

    def score(self, tick: int) -> float:
        return self.quality * self.confidence(tick)


class Memory(BaseModel):
    food: list[MemoryEntry] = []
    water: list[MemoryEntry] = []
    shelter: list[MemoryEntry] = []

    def observe(self, pos: tuple[int, int], kind: str, quality: float, tick: int) -> None:
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

    def query(self, kind: str, tick: int, urgency: float = 0.0) -> tuple[int, int] | None:
        
        entries = [e for e in self._bucket(kind) if e.confidence(tick) >= CONFIDENCE_PRUNE]
        self._set_bucket(kind, entries)
        
        if not entries:
            return None
        
        return max(entries, key=lambda e: e.score(tick)).pos

    def _bucket(self, kind: str) -> list[MemoryEntry]:
        return {"food": self.food, "water": self.water, "shelter": self.shelter}[kind]

    def _set_bucket(self, kind: str, entries: list[MemoryEntry]) -> None:
        match kind:
            case "food":    self.food = entries
            case "water":   self.water = entries
            case "shelter": self.shelter = entries
