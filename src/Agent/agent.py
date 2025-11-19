import numpy as np
from typing import Optional

MATURITY_AGE = 50
REPRODUCTION_ENERGY_THRESHOLD = 150
SEARCH_RADIUS = 5

class Agent:
  def __init__(self, agent_id, position, initial_energy=100):
    self.id = agent_id
    self.position = position
    self.energy = initial_energy
    self.age = 0
    self.alive = True
    self.metabolism_rate = 1
    
  def tick(self):
    if not self.alive:
      return
    
    self.age += 1
    self.energy -= self.metabolism_rate

    if self.energy <= 0:
      self.die()
      
  def die(self):
    self.alive = False
    
  def can_reproduce(self):
    return (
      self.alive and
      self.age >= MATURITY_AGE and
      self.energy >= REPRODUCTION_ENERGY_THRESHOLD
    )
    
  def reproduce(self, new_agent_id):
    if not self.can_reproduce():
      return None
    
    self.energy -= 50
    offspring = Agent(agent_id=new_agent_id, position=self.position, initial_energy=50)
    return offspring
  
  def eat(self, food_energy=20):
    self.energy += food_energy
    self.energy = min(self.energy, 200)
    
  def move(self, new_position):
    self.position = new_position
    
  def move_random(self, world) -> None:
    if not self.alive:
      return
    
    dx = np.random.choice([-1, 0, 1])
    dy = np.random.choice([-1, 0, 1])
    
    new_x = self.position[0] + dx
    new_y = self.position[1] + dy
    
    if world.is_valid_position(new_x, new_y):
      self.position = (new_x, new_y)
      
  def move_to_closest_food(self, resources_manager):
    nearby_food = resources_manager.get_food_in_radius(self.position, SEARCH_RADIUS)
    
    if not nearby_food:
      self.move_random(resources_manager.world)
      return
    
    x, y = self.position
    
    closest_food = min(
      nearby_food,
      key=lambda food_pos: (food_pos[0] - x) ** 2 + (food_pos[1] - y) ** 2
    )
    
    if closest_food == self.position:
      self.eat()
      resources_manager.remove_food(closest_food)
      return
    
    direction_x = np.sign(closest_food[0] - self.position[0])
    direction_y = np.sign(closest_food[1] - self.position[1])

    new_x = self.position[0] + direction_x
    new_y = self.position[1] + direction_y

    if resources_manager.world.is_valid_position(new_x, new_y):
      self.position = (new_x, new_y)