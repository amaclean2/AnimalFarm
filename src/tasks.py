from dataclasses import dataclass, field

PRIORITY_RETURN_HOME = 20
PRIORITY_SEEK_FOOD = 30
PRIORITY_MATE = 40
PRIORITY_SEEK_FOOD_SATED = 60
PRIORITY_EXPLORE = 100


@dataclass(order=True)
class Task:
    priority: int
    name: str = field(compare=False)
    goal_pos: tuple[int, int] = field(compare=False)
