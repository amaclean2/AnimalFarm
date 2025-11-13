import numpy as np
from typing import Tuple, Optional

class World:
  def __init__(self, width: int = 200, height: int = 200):
    self.width = width
    self.height = height
    self.grid = np.zeros((height, width), dtype=np.int32)
    
  def is_valid_position(self, x: int, y: int) -> bool:
    return 0 <= x < self.width and 0 <= y < self.height
  
  def get_neighbors(self, x: int, y: int, radius: int = 1) -> list[Tuple[int, int]]:
    neighbors = []
    for dx in range(-radius, radius + 1):
      for dy in range(-radius, radius + 1):
        if dx == 0 and dy == 0:
          continue
        
        nx, ny = x + dx, y + dy
        
        if self.is_valid_position(nx, ny):
          neighbors.append((nx, ny))
          
    return neighbors