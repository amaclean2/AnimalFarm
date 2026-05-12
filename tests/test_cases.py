import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent import MAX_HEALTH
from scenario import Scenario


@dataclass
class TestCase(Scenario):
    max_ticks: int = 200
    assert_fn: Callable = field(default=lambda world, agent, tick: True)
    failure_message: str = "test failed"


TEST_CASES = [
    TestCase(
        name="Agent crosses board and eats from opposite corner",
        description="Adult agent at (0,0) with 40 hp, food at (9,9) — should cross the full board and eat",
        agent_x=0,
        agent_y=0,
        agent_health=40,
        agent_is_adult=True,
        food=[(9, 9)],
        stop_when=lambda world, tick: not world.all_food(),
        max_ticks=22,
        assert_fn=lambda world, agent, tick: tick is not None and agent.alive and agent.health == MAX_HEALTH,
        failure_message="agent never reached the food",
    ),
    TestCase(
        name="Agent eats nearby food",
        description="Agent at 40 hp, food one step away — should pathfind straight to it and eat",
        agent_health=40,
        food=[(6, 5)],
        stop_when=lambda world, tick: not world.all_food(),
        assert_fn=lambda world, agent, tick: tick is not None and agent.health == MAX_HEALTH,
        failure_message="agent never ate the food",
    ),
    TestCase(
        name="Agent starves on empty board",
        description="No food anywhere — agent should eventually starve",
        stop_when=lambda world, tick: not world.all_living_agents(),
        assert_fn=lambda world, agent, tick: not agent.alive,
        failure_message="agent did not starve",
    ),
    TestCase(
        name="Adjacent food",
        description="Food on all four adjacent cells — agent should eat within 3 ticks",
        food=[(4, 5), (6, 5), (5, 4), (5, 6)],
        stop_when=lambda world, tick: any(a.health == MAX_HEALTH for a in world.all_living_agents()),
        max_ticks=3,
        assert_fn=lambda world, agent, tick: tick is not None,
        failure_message="agent didn't eat within 3 ticks of adjacent food",
    ),
    TestCase(
        name="Corner food",
        description="Single food item in the far corner — tests long-range pathfinding",
        food=[(9, 9)],
        stop_when=lambda world, tick: not world.all_food(),
        max_ticks=100,
        assert_fn=lambda world, agent, tick: tick is not None,
        failure_message="agent never reached corner food",
    ),
    TestCase(
        name="Low health agent survives with nearby food",
        description="Agent near death with food one step away — should survive",
        agent_health=5,
        food=[(6, 5)],
        stop_when=lambda world, tick: not world.all_living_agents() or any(a.health == MAX_HEALTH for a in world.all_living_agents()),
        assert_fn=lambda world, agent, tick: agent.alive,
        failure_message="agent died before reaching food one step away",
    ),
]
