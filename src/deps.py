from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agents
    from genome_pool import GenomePool
    from plant import VegetationManager
    from simulation import Simulation
    from world import World

world: World
vegetation: VegetationManager
agents: Agents
simulation: Simulation
genome_pool: GenomePool
