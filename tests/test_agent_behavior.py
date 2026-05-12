from agent import MAX_HEALTH
from scenario import Scenario
from conftest import setup_scenario, run_until

SCENARIOS = [
    Scenario(
        name="Agent crosses board and east from opposite corner",
        description="Adult agent at (0,0) with 40 hp, food at (9,9) — should cross the full board and eat",
        agent_x=0,
        agent_y=0,
        agent_health=40,
        agent_is_adult=True,
        food=[(9, 9)],
        stop_when=lambda world, tick: not world.all_food(),
    ),
    Scenario(
        name="Agent eats nearby food",
        description="Agent at 40 hp, food one step away — should pathfind straight to it and eat",
        agent_health=40,
        food=[(6, 5)],
        stop_when=lambda world, tick: not world.all_food(),
    ),
    Scenario(
        name="Agent starves on empty board",
        description="No food anywhere — watch the agent explore and starve",
        stop_when=lambda world, tick: not world.all_living_agents(),
    ),
    Scenario(
        name="Adjacent food",
        description="Food on all four adjacent cells — agent should eat within 3 ticks",
        food=[(4, 5), (6, 5), (5, 4), (5, 6)],
        stop_when=lambda world, tick: any(a.health == MAX_HEALTH for a in world.all_living_agents()),
    ),
    Scenario(
        name="Corner food",
        description="Single food item in the far corner — tests long-range pathfinding",
        food=[(9, 9)],
        stop_when=lambda world, tick: not world.all_food(),
    ),
    Scenario(
        name="Low health, food nearby",
        description="Agent near death with food one step away — should survive",
        agent_health=5,
        food=[(6, 5)],
        stop_when=lambda world, tick: not world.all_living_agents() or any(a.health == MAX_HEALTH for a in world.all_living_agents()),
    ),
]


def test_agent_crosses_board_and_eats_from_opposite_corner():
    world, sim, agent = setup_scenario(SCENARIOS[0])
    tick = run_until(sim, world, lambda w, _: not w.all_food(), max_ticks=22)
    assert tick is not None, "agent never reached the food"
    assert agent.alive
    assert agent.health == MAX_HEALTH


def test_agent_eats_nearby_food():
    world, sim, agent = setup_scenario(SCENARIOS[1])
    tick = run_until(sim, world, lambda w, _: not w.all_food())
    assert tick is not None, "agent never ate the food"
    assert agent.health == MAX_HEALTH


def test_agent_starves_on_empty_board():
    world, sim, agent = setup_scenario(SCENARIOS[2])
    run_until(sim, world, lambda w, _: not w.all_living_agents())
    assert not agent.alive


def test_agent_eats_adjacent_food_immediately():
    world, sim, agent = setup_scenario(SCENARIOS[3])
    tick = run_until(sim, world, lambda w, _: agent.health == MAX_HEALTH, max_ticks=3)
    assert tick is not None, "agent didn't eat within 3 ticks of adjacent food"


def test_agent_reaches_corner_food():
    world, sim, agent = setup_scenario(SCENARIOS[4])
    tick = run_until(sim, world, lambda w, _: not w.all_food(), max_ticks=100)
    assert tick is not None, "agent never reached corner food"


def test_low_health_agent_survives_with_nearby_food():
    world, sim, agent = setup_scenario(SCENARIOS[5])
    run_until(sim, world, lambda w, _: not w.all_living_agents() or agent.health == MAX_HEALTH)
    assert agent.alive, "agent died before reaching food one step away"
