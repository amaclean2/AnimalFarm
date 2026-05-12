from uuid import UUID, uuid4

from pydantic import BaseModel, Field

MAX_HEALTH = 80
MAX_REST = 80
REST_THRESHOLD_DEFAULT = 20
NIGHT_DRAIN_DEFAULT = 4
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
    birth_tick: int = 0
    mutations: list[str] = Field(default_factory=list)
    genotype: dict[str, int] = Field(default_factory=dict)
    metabolism: float = 1.0
    is_adult: bool = False
    rest: int = MAX_REST
    rest_threshold: int = REST_THRESHOLD_DEFAULT
    night_drain: int = NIGHT_DRAIN_DEFAULT
    is_sleeping: bool = False
