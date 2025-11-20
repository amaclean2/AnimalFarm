import numpy as np
from typing import List, Dict
from Agent.agent import Agent
from World.world import World
from World.resources import ResourceManager

class Simulation:
  def __init__(self, world: World, resource_manager: ResourceManager, initial_population: int = 100):
    self.world = world
    self.resource_manager = resource_manager
    self.agents: List[Agent] = []
    self.next_agent_id = 0
    self.current_tick = 0
    
    # Metrics tracking
    self.metrics = {
      'population': [],
      'births': [],
      'deaths': [],
      'total_births': 0,
      'total_deaths': 0,
      'ages_at_death': []
    }
    
    # Initialize population
    for _ in range(initial_population):
      self._spawn_agent()
  
  def _spawn_agent(self, position=None, initial_energy=100):
    """Spawn a new agent at a random or specified position"""
    if position is None:
      x = np.random.randint(0, self.world.width)
      y = np.random.randint(0, self.world.height)
      position = (x, y)
    
    agent = Agent(agent_id=self.next_agent_id, position=position, initial_energy=initial_energy)
    self.agents.append(agent)
    self.next_agent_id += 1
    return agent
  
  def tick(self):
    """Execute one simulation step"""
    births_this_tick = 0
    deaths_this_tick = 0
    
    # Process resource regeneration
    self.resource_manager.step()
    
    # Process each agent
    alive_agents = [agent for agent in self.agents if agent.alive]
    
    for agent in alive_agents:
      # Agent ages and consumes energy
      agent.tick()
      
      if not agent.alive:
        deaths_this_tick += 1
        self.metrics['total_deaths'] += 1
        self.metrics['ages_at_death'].append(agent.age)
        continue
      
      # Agent moves towards food or randomly (and eats if already on food)
      agent.move_to_closest_food(self.resource_manager)
      
      # Agent reproduces if able
      if agent.can_reproduce():
        offspring = agent.reproduce(new_agent_id=self.next_agent_id)
        if offspring is not None:
          self.agents.append(offspring)
          self.next_agent_id += 1
          births_this_tick += 1
          self.metrics['total_births'] += 1
    
    # Update metrics
    self.current_tick += 1
    alive_count = sum(1 for agent in self.agents if agent.alive)
    self.metrics['population'].append(alive_count)
    self.metrics['births'].append(births_this_tick)
    self.metrics['deaths'].append(deaths_this_tick)
  
  def run(self, num_ticks: int):
    """Run the simulation for a specified number of ticks"""
    for _ in range(num_ticks):
      self.tick()
  
  def get_alive_agents(self) -> List[Agent]:
    """Get list of currently alive agents"""
    return [agent for agent in self.agents if agent.alive]
  
  def get_population_count(self) -> int:
    """Get current population count"""
    return sum(1 for agent in self.agents if agent.alive)
  
  def get_average_lifespan(self) -> float:
    """Calculate average lifespan of dead agents"""
    if not self.metrics['ages_at_death']:
      return 0.0
    return np.mean(self.metrics['ages_at_death'])
  
  def get_metrics(self) -> Dict:
    """Get all tracked metrics"""
    return {
      'current_tick': self.current_tick,
      'current_population': self.get_population_count(),
      'total_births': self.metrics['total_births'],
      'total_deaths': self.metrics['total_deaths'],
      'average_lifespan': self.get_average_lifespan(),
      'population_history': self.metrics['population'],
      'births_history': self.metrics['births'],
      'deaths_history': self.metrics['deaths']
    }
