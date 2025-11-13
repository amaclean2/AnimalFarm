import numpy as np
from typing import Tuple, Optional
from .world import World

class ResourceManager:
  def __init__(self, world: World, initial_food_count: int = 500, regen_rate: float = 0.01):
    self.world = world
    self.food_positions = set()
    self.regen_rate = regen_rate
    self.spawn_initial_food(initial_food_count)
    
  def spawn_initial_food(self, count: int):
    for _ in range(count):
      x = np.random.randint(0, self.world.width)
      y = np.random.randint(0, self.world.height)
      self.add_food((x, y))
      
  def add_food(self, position: Tuple[int, int]):
    if self.world.is_valid_position(*position):
      self.food_positions.add(position)
      self.world.grid[position[1], position[0]] = 1
      
  def remove_food(self, position: Tuple[int, int]) -> bool:
    if position in self.food_positions:
      self.food_positions.remove(position)
      self.world.grid[position[1], position[0]] = 0
      return True
    
    return False
  
  def has_food(self, position: Tuple[int, int]) -> bool:
    return position in self.food_positions

  def step(self):
    max_food = self.world.width * self.world.height // 10 # Max 10% coverage
    current_food = len(self.food_positions)
    
    if current_food < max_food:
      if np.random.rand() < self.regen_rate:
        x = np.random.randint(0, self.world.width)
        y = np.random.randint(0, self.world.height)
        if not self.has_food((x, y)):
          self.add_food((x, y))
          
  def get_food_in_radius(self, position: Tuple[int, int], radius: int) -> list[Tuple[int, int]]:
    nearby_food = []
    for fx, fy in self.food_positions:
      dist_sq = (fx - position[0]) ** 2 + (fy - position[1]) ** 2
      
      if dist_sq <= radius ** 2:
        nearby_food.append((fx, fy))
        
    return nearby_food