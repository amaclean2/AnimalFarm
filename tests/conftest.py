import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from world import World
from simulation import Simulation
from scenario import Scenario


def make_sim(width: int = 10, height: int = 10) -> tuple[World, Simulation]:
    w = World(width=width, height=height)
    s = Simulation(w)
    s._game_logged = True
    return w, s


def run_until(sim: Simulation, world: World, condition, max_ticks: int = 200) -> int | None:
    """Tick until condition(world, tick) is truthy. Returns the tick it fired on, or None."""
    for tick in range(1, max_ticks + 1):
        sim.on_tick(tick)
        if condition(world, tick):
            return tick
    return None


def setup_scenario(scenario: Scenario):
    """Build a world and sim from a Scenario. Returns (world, sim, agent)."""
    world, sim = make_sim()
    agent = world.add_agent(scenario.agent_x, scenario.agent_y)
    agent.health = scenario.agent_health
    agent.age = scenario.agent_age
    agent.is_adult = scenario.agent_is_adult
    for x, y in scenario.food:
        if world.get_food_at(x, y) is None:
            world.place_food(x, y)
    return world, sim, agent
