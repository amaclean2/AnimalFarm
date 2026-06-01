from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agents
    from food import FoodManager
    from simulation import Simulation
    from world import World

world: World
food: FoodManager
agents: Agents
simulation: Simulation
