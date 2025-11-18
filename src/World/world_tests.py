import unittest

from world import World
from resources import ResourceManager

WORLD_SIZE = 200

class TestWorldIntegration(unittest.TestCase):
  
  def test_position_validation(self):
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    
    self.assertTrue(world.is_valid_position(0, 0))
    self.assertTrue(world.is_valid_position(WORLD_SIZE - 1, WORLD_SIZE - 1))
    self.assertFalse(world.is_valid_position(-1, 0))
    self.assertFalse(world.is_valid_position(0, -1))
    self.assertFalse(world.is_valid_position(WORLD_SIZE, WORLD_SIZE))
  
  def test_get_neighbors(self):
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    
    neighbors = world.get_neighbors(1, 1, radius=1)
    expected_neighbors = [
      (0, 0), (0, 1), (0, 2),
      (1, 0),         (1, 2),
      (2, 0), (2, 1), (2, 2)
    ]
    
    self.assertCountEqual(neighbors, expected_neighbors)
    
    edge_neighbors = world.get_neighbors(0, 0, radius=1)
    expected_edge_neighbors = [(0, 1), (1, 0), (1, 1)]
    
    self.assertCountEqual(edge_neighbors, expected_edge_neighbors)
    
class TestResourceManagerIntegration(unittest.TestCase):
  
  def test_initial_food_spawn(self):
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    resource_manager = ResourceManager(world, initial_food_count=100)
    
    self.assertEqual(len(resource_manager.food_positions), 100)
    
    for pos in resource_manager.food_positions:
      self.assertTrue(world.is_valid_position(*pos))
      self.assertEqual(world.grid[pos[1], pos[0]], 1)
  
  def test_food_addition_and_removal(self):
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    position = (10, 10)
    resource_manager.add_food(position)
    
    self.assertTrue(resource_manager.has_food(position))
    self.assertEqual(world.grid[position[1], position[0]], 1)
    
    removed = resource_manager.remove_food(position)
    self.assertTrue(removed)
    self.assertFalse(resource_manager.has_food(position))
    self.assertEqual(world.grid[position[1], position[0]], 0)
    
if __name__ == '__main__':
  unittest.main()