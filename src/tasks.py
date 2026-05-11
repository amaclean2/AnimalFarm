from dataclasses import dataclass, field

PRIORITY_CARRY_FOOD = 10
PRIORITY_EAT_STOCKPILE = 20
PRIORITY_SEEK_FOOD = 30
PRIORITY_MATE = 40
PRIORITY_EXPLORE = 100


@dataclass(order=True)
class Task:
    priority: int
    name: str = field(compare=False)
    goal_pos: tuple[int, int] = field(compare=False)
