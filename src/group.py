import math
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

BASE_GRAVITY = 1.0
BASE_COHESION = 5.0
ATTRACTION_MULTIPLIER = 2.0
VISION_BONUS = 1.5


class Group(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    member_ids: set[UUID] = Field(default_factory=set)
    center_x: float = 0.0
    center_y: float = 0.0
    home: tuple[int, int] | None = None
    stockpile: int = 0

    @property
    def size(self) -> int:
        return len(self.member_ids)

    @property
    def gravity(self) -> float:
        return BASE_GRAVITY * math.sqrt(max(self.size, 1))

    @property
    def cohesion_radius(self) -> float:
        return BASE_COHESION * self.gravity

    @property
    def attraction_range(self) -> float:
        return self.cohesion_radius * ATTRACTION_MULTIPLIER

    def update_center(self, agents: list) -> None:
        if not agents:
            return
        self.center_x = sum(a.x for a in agents) / len(agents)
        self.center_y = sum(a.y for a in agents) / len(agents)
