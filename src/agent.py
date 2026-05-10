from uuid import UUID, uuid4

from pydantic import BaseModel, Field

MAX_HEALTH = 80
VISION_RANGE = 20


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
    carrying_food: bool = False
    birth_tick: int = 0
    mutation: str | None = None
    metabolism: float = 1.0
