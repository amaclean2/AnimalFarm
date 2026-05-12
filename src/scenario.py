from dataclasses import dataclass, field
from typing import Callable

MAX_HEALTH = 80
BOARD = 10


@dataclass
class Scenario:
    name: str
    description: str = ""
    agent_x: int = BOARD // 2
    agent_y: int = BOARD // 2
    agent_health: int = MAX_HEALTH
    agent_age: int = 0
    agent_is_adult: bool = False
    food: list[tuple[int, int]] = field(default_factory=list)
    stop_when: Callable | None = None
