import unittest

from agent import Agent, MATURITY_AGE, REPRODUCTION_ENERGY_THRESHOLD

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
    
if __name__ == '__main__':
  unittest.main()