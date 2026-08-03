from pydantic import BaseModel, Field

from config import INVENTORY_CAPACITY


class Inventory(BaseModel):
    items: dict[str, float] = Field(default_factory=dict)

    @property
    def total(self) -> float:
        return sum(self.items.values())

    @property
    def is_full(self) -> bool:
        return self.total >= INVENTORY_CAPACITY

    @property
    def fullness(self) -> float:
        return self.total / INVENTORY_CAPACITY

    def has(self, kind: str) -> bool:
        return self.items.get(kind, 0.0) > 0.0

    def add(self, kind: str, quantity: float = 1.0) -> bool:
        if self.total + quantity > INVENTORY_CAPACITY:
            return False
        self.items[kind] = self.items.get(kind, 0.0) + quantity
        return True

    def take(self, kind: str, quantity: float = 1.0) -> float:
        available = self.items.get(kind, 0.0)
        taken = min(available, quantity)
        remaining = available - taken

        if remaining > 0.0:
            self.items[kind] = remaining
        else:
            self.items.pop(kind, None)

        return taken
