import unittest
import sys
import os

# Add parent directory to path to import World modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'World'))

from agent import Agent, MATURITY_AGE, REPRODUCTION_ENERGY_THRESHOLD, SEARCH_RADIUS
from world import World
from resources import ResourceManager

class TestAgentLifecycleIntegration(unittest.TestCase):
  def test_complete_lifecycle_until_death(self):
    agent = Agent(agent_id=1, position=(0, 0), initial_energy=5)
    
    self.assertTrue(agent.alive)
    self.assertEqual(agent.age, 0)
    
    for i in range(4):
      agent.tick()
      self.assertTrue(agent.alive)
      self.assertEqual(agent.age, i + 1)
      
    agent.tick()
    self.assertFalse(agent.alive)
    self.assertEqual(agent.energy, 0)
    
  
  def test_lifecycle_with_eating_and_reproduction(self):
    agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
    
    for _ in range(MATURITY_AGE):
      agent.tick()
      
    self.assertEqual(agent.age, MATURITY_AGE)
    self.assertEqual(agent.energy, 100 - MATURITY_AGE)
    
    food_needed = REPRODUCTION_ENERGY_THRESHOLD - agent.energy
    agent.eat(food_energy=food_needed)
    
    self.assertTrue(agent.can_reproduce())
    
    offspring = agent.reproduce(new_agent_id=2)
    self.assertIsNotNone(offspring)
    self.assertEqual(offspring.id, 2)
    self.assertTrue(offspring.alive)
    self.assertEqual(offspring.energy, 50)
  
  def test_tick_and_move_interaction(self):
    agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
    
    agent.move((5, 5))
    agent.tick()
    
    self.assertEqual(agent.position, (5, 5))
    self.assertEqual(agent.age, 1)
    self.assertEqual(agent.energy, 99)
    self.assertTrue(agent.alive)

class TestAgentMovement(unittest.TestCase):
  def test_move_random_changes_position(self):
    """Test that move_random changes agent position within valid bounds"""
    world = World(width=10, height=10)
    agent = Agent(agent_id=1, position=(5, 5), initial_energy=100)
    
    initial_position = agent.position
    
    # Run multiple times to ensure movement happens (may stay in place if dx=0, dy=0)
    moved = False
    for _ in range(20):
      agent.move_random(world)
      if agent.position != initial_position:
        moved = True
        break
    
    self.assertTrue(moved, "Agent should move from initial position after multiple attempts")
    self.assertTrue(world.is_valid_position(*agent.position))
    
    # Check that position is within one step of initial position
    dx = abs(agent.position[0] - initial_position[0])
    dy = abs(agent.position[1] - initial_position[1])
    self.assertLessEqual(dx, 1, "X movement should be at most 1")
    self.assertLessEqual(dy, 1, "Y movement should be at most 1")
  
  def test_move_random_respects_world_boundaries(self):
    """Test that move_random doesn't move agent outside world boundaries"""
    world = World(width=10, height=10)
    
    # Test corner positions
    corner_positions = [(0, 0), (0, 9), (9, 0), (9, 9)]
    
    for pos in corner_positions:
      agent = Agent(agent_id=1, position=pos, initial_energy=100)
      
      # Run multiple times to ensure boundary checking works
      for _ in range(50):
        agent.move_random(world)
        self.assertTrue(world.is_valid_position(*agent.position), 
                       f"Position {agent.position} should be valid after moving from corner {pos}")
        self.assertGreaterEqual(agent.position[0], 0)
        self.assertLess(agent.position[0], 10)
        self.assertGreaterEqual(agent.position[1], 0)
        self.assertLess(agent.position[1], 10)
  
  def test_move_random_dead_agent_does_not_move(self):
    """Test that dead agents don't move"""
    world = World(width=10, height=10)
    agent = Agent(agent_id=1, position=(5, 5), initial_energy=100)
    
    agent.die()
    initial_position = agent.position
    
    agent.move_random(world)
    
    self.assertEqual(agent.position, initial_position, "Dead agent should not move")
    self.assertFalse(agent.alive)
  
  def test_move_to_closest_food_moves_towards_food(self):
    """Test that agent moves towards closest food"""
    world = World(width=20, height=20)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    # Place agent and food
    agent = Agent(agent_id=1, position=(10, 10), initial_energy=100)
    food_position = (13, 13)  # Within SEARCH_RADIUS
    resource_manager.add_food(food_position)
    
    initial_position = agent.position
    agent.move_to_closest_food(resource_manager)
    
    # Check that agent moved closer to food
    initial_distance = (food_position[0] - initial_position[0]) ** 2 + (food_position[1] - initial_position[1]) ** 2
    new_distance = (food_position[0] - agent.position[0]) ** 2 + (food_position[1] - agent.position[1]) ** 2
    
    self.assertLess(new_distance, initial_distance, "Agent should move closer to food")
    self.assertNotEqual(agent.position, initial_position, "Agent should have moved")
  
  def test_move_to_closest_food_eats_when_on_food(self):
    """Test that agent eats food when positioned on it"""
    world = World(width=20, height=20)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    # Place agent and food at same position
    position = (10, 10)
    agent = Agent(agent_id=1, position=position, initial_energy=100)
    resource_manager.add_food(position)
    
    initial_energy = agent.energy
    
    agent.move_to_closest_food(resource_manager)
    
    # Agent should have eaten the food
    self.assertEqual(agent.energy, initial_energy + 20, "Agent should have gained energy from eating")
    self.assertFalse(resource_manager.has_food(position), "Food should be removed after eating")
  
  def test_move_to_closest_food_moves_random_when_no_food(self):
    """Test that agent moves randomly when no food is in radius"""
    world = World(width=20, height=20)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    # Place agent with no food nearby
    agent = Agent(agent_id=1, position=(10, 10), initial_energy=100)
    
    initial_position = agent.position
    
    # Run multiple times to ensure random movement happens
    moved = False
    for _ in range(20):
      agent.position = initial_position  # Reset position
      agent.move_to_closest_food(resource_manager)
      if agent.position != initial_position:
        moved = True
        break
    
    self.assertTrue(moved, "Agent should move randomly when no food is nearby")
  
  def test_move_to_closest_food_selects_closest_among_multiple(self):
    """Test that agent moves towards the closest food when multiple foods are present"""
    world = World(width=20, height=20)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    # Place agent and multiple foods
    agent = Agent(agent_id=1, position=(10, 10), initial_energy=100)
    close_food = (12, 12)  # Distance squared = 8
    far_food = (14, 14)    # Distance squared = 32
    resource_manager.add_food(close_food)
    resource_manager.add_food(far_food)
    
    agent.move_to_closest_food(resource_manager)
    
    # Check that agent moved closer to the closest food
    distance_to_close = (close_food[0] - agent.position[0]) ** 2 + (close_food[1] - agent.position[1]) ** 2
    distance_to_far = (far_food[0] - agent.position[0]) ** 2 + (far_food[1] - agent.position[1]) ** 2
    
    self.assertLess(distance_to_close, distance_to_far, 
                   "Agent should be closer to the originally closest food")
    
if __name__ == '__main__':
  unittest.main()