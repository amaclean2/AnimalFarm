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
  
  def test_get_food_in_radius(self):
    """Test that get_food_in_radius returns food within specified radius"""
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    center_position = (50, 50)
    radius = 5
    
    # Add food at various distances from center
    food_within_radius = [
      (50, 50),  # At center (distance 0)
      (53, 50),  # Distance 3
      (50, 54),  # Distance 4
      (53, 54),  # Distance 5 (exactly on boundary)
    ]
    
    food_outside_radius = [
      (50, 56),  # Distance 6
      (57, 50),  # Distance 7
      (45, 40),  # Distance sqrt(125) ≈ 11.2
    ]
    
    # Add all food
    for pos in food_within_radius:
      resource_manager.add_food(pos)
    
    for pos in food_outside_radius:
      resource_manager.add_food(pos)
    
    # Get food in radius
    nearby_food = resource_manager.get_food_in_radius(center_position, radius)
    
    # Verify results
    self.assertEqual(len(nearby_food), len(food_within_radius), 
                    f"Should find {len(food_within_radius)} food items within radius")
    
    for pos in food_within_radius:
      self.assertIn(pos, nearby_food, f"Food at {pos} should be within radius {radius}")
    
    for pos in food_outside_radius:
      self.assertNotIn(pos, nearby_food, f"Food at {pos} should be outside radius {radius}")
  
  def test_get_food_in_radius_empty(self):
    """Test that get_food_in_radius returns empty list when no food present"""
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    center_position = (50, 50)
    radius = 5
    
    nearby_food = resource_manager.get_food_in_radius(center_position, radius)
    
    self.assertEqual(len(nearby_food), 0, "Should return empty list when no food is present")
    self.assertIsInstance(nearby_food, list, "Should return a list")
  
  def test_get_food_in_radius_large_radius(self):
    """Test get_food_in_radius with a large radius"""
    world = World(width=WORLD_SIZE, height=WORLD_SIZE)
    resource_manager = ResourceManager(world, initial_food_count=0)
    
    center_position = (100, 100)
    radius = 50
    
    # Add food at various positions
    food_positions = [
      (100, 100),  # At center
      (120, 120),  # Within radius
      (100, 149),  # Just within radius (distance 49)
      (100, 151),  # Just outside radius (distance 51)
    ]
    
    for pos in food_positions:
      resource_manager.add_food(pos)
    
    nearby_food = resource_manager.get_food_in_radius(center_position, radius)
    
    # Should include first 3, exclude last one
    self.assertGreaterEqual(len(nearby_food), 3, "Should find at least 3 food items")
    self.assertIn((100, 100), nearby_food)
    self.assertIn((120, 120), nearby_food)
    self.assertIn((100, 149), nearby_food)
    
if __name__ == '__main__':
  unittest.main()