import unittest
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(__file__))

from simulation import Simulation
from World.world import World
from World.resources import ResourceManager
from Agent.agent import Agent

class TestSimulationBasics(unittest.TestCase):
  def test_simulation_initialization(self):
    """Test that simulation initializes with correct population"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=10)
    
    self.assertEqual(len(sim.agents), 10)
    self.assertEqual(sim.get_population_count(), 10)
    self.assertEqual(sim.current_tick, 0)
    self.assertEqual(sim.next_agent_id, 10)
  
  def test_simulation_tick_increments(self):
    """Test that tick counter increments properly"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    self.assertEqual(sim.current_tick, 0)
    sim.tick()
    self.assertEqual(sim.current_tick, 1)
    sim.tick()
    self.assertEqual(sim.current_tick, 2)
  
  def test_simulation_run(self):
    """Test that run executes multiple ticks"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    sim.run(10)
    self.assertEqual(sim.current_tick, 10)
    self.assertEqual(len(sim.metrics['population']), 10)

class TestSimulationMetrics(unittest.TestCase):
  def test_population_tracking(self):
    """Test that population is tracked over time"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    sim.run(5)
    
    self.assertEqual(len(sim.metrics['population']), 5)
    self.assertTrue(all(isinstance(p, (int, np.int64)) for p in sim.metrics['population']))
  
  def test_births_tracking(self):
    """Test that births are tracked"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    sim.run(5)
    
    self.assertEqual(len(sim.metrics['births']), 5)
    self.assertTrue(all(isinstance(b, int) for b in sim.metrics['births']))
    self.assertEqual(sum(sim.metrics['births']), sim.metrics['total_births'])
  
  def test_deaths_tracking(self):
    """Test that deaths are tracked"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=0)  # No food causes deaths
    sim = Simulation(world, resource_manager, initial_population=5)
    
    # Run enough ticks for agents to die (initial energy 100, metabolism 1)
    sim.run(110)
    
    self.assertGreater(sim.metrics['total_deaths'], 0)
    self.assertEqual(sum(sim.metrics['deaths']), sim.metrics['total_deaths'])
    self.assertEqual(len(sim.metrics['ages_at_death']), sim.metrics['total_deaths'])
  
  def test_get_metrics(self):
    """Test that get_metrics returns correct structure"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=100)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    sim.run(5)
    
    metrics = sim.get_metrics()
    
    self.assertIn('current_tick', metrics)
    self.assertIn('current_population', metrics)
    self.assertIn('total_births', metrics)
    self.assertIn('total_deaths', metrics)
    self.assertIn('average_lifespan', metrics)
    self.assertIn('population_history', metrics)
    self.assertIn('births_history', metrics)
    self.assertIn('deaths_history', metrics)
    
    self.assertEqual(metrics['current_tick'], 5)

class TestSimulationLifecycle(unittest.TestCase):
  def test_agent_death_in_simulation(self):
    """Test that agents die when energy is depleted"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=0)  # No food available to test starvation
    sim = Simulation(world, resource_manager, initial_population=5)
    
    initial_population = sim.get_population_count()
    
    # Run enough ticks for all agents to die (with metabolism rate 1, initial energy 100)
    sim.run(105)
    
    final_population = sim.get_population_count()
    
    self.assertEqual(initial_population, 5)
    # All agents should have died or be very close to death
    self.assertLessEqual(final_population, 1)
    self.assertGreaterEqual(sim.metrics['total_deaths'], 4)
  
  def test_agent_reproduction_in_simulation(self):
    """Test that agents reproduce when conditions are met"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=500)  # Abundant food to enable reproduction
    sim = Simulation(world, resource_manager, initial_population=5)
    
    # Create mature agents with high energy
    for agent in sim.agents:
      agent.age = 50  # Maturity age
      agent.energy = 160  # Above reproduction threshold
    
    initial_population = sim.get_population_count()
    
    # Run one tick - should have reproductions
    sim.tick()
    
    final_population = sim.get_population_count()
    
    self.assertGreater(final_population, initial_population)
    self.assertGreater(sim.metrics['total_births'], 0)
  
  def test_agent_eating_in_simulation(self):
    """Test that agents eat food when present"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=0)
    sim = Simulation(world, resource_manager, initial_population=1)
    
    agent = sim.agents[0]
    agent.position = (25, 25)
    agent.energy = 100
    
    # Place food at agent position
    resource_manager.add_food((25, 25))
    
    self.assertTrue(resource_manager.has_food((25, 25)))
    
    sim.tick()
    
    # Agent should have eaten the food
    self.assertFalse(resource_manager.has_food((25, 25)))
    self.assertGreater(agent.energy, 100)  # Energy increased after eating
  
  def test_average_lifespan_calculation(self):
    """Test that average lifespan is calculated correctly"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=0)
    sim = Simulation(world, resource_manager, initial_population=3)
    
    # Set different initial energies for different lifespans
    sim.agents[0].energy = 10  # Will die at age 10
    sim.agents[1].energy = 20  # Will die at age 20
    sim.agents[2].energy = 30  # Will die at age 30
    
    sim.run(35)
    
    avg_lifespan = sim.get_average_lifespan()
    
    # Average of 10, 20, 30 is 20
    self.assertEqual(avg_lifespan, 20.0)
  
  def test_get_alive_agents(self):
    """Test that get_alive_agents returns only living agents"""
    world = World(width=50, height=50)
    resource_manager = ResourceManager(world, initial_food_count=0)
    sim = Simulation(world, resource_manager, initial_population=5)
    
    # Kill some agents manually
    sim.agents[0].die()
    sim.agents[1].die()
    
    alive_agents = sim.get_alive_agents()
    
    self.assertEqual(len(alive_agents), 3)
    self.assertTrue(all(agent.alive for agent in alive_agents))

if __name__ == '__main__':
  unittest.main()
