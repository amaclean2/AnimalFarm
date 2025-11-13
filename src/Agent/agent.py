MATURITY_AGE = 50
REPRODUCTION_ENERGY_THRESHOLD = 150

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