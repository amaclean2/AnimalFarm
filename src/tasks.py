from dataclasses import dataclass, field

PRIORITY_SEEK_FOOD = 30
PRIORITY_MATE = 40
PRIORITY_EXPLORE = 100


@dataclass(order=True)
class Task:
    priority: int
    name: str = field(compare=False)
    goal_pos: tuple[int, int] = field(compare=False)
