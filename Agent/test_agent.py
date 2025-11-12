import unittest
from Agent import Agent, MATURITY_AGE, REPRODUCTION_ENERGY_THRESHOLD


class TestAgentInitialization(unittest.TestCase):
    """Test Agent initialization"""
    
    def test_init_with_defaults(self):
        """Test agent initialization with default energy"""
        agent = Agent(agent_id=1, position=(0, 0))
        self.assertEqual(agent.id, 1)
        self.assertEqual(agent.position, (0, 0))
        self.assertEqual(agent.energy, 100)
        self.assertEqual(agent.age, 0)
        self.assertTrue(agent.alive)
    
    def test_init_with_custom_energy(self):
        """Test agent initialization with custom energy"""
        agent = Agent(agent_id=2, position=(5, 10), initial_energy=150)
        self.assertEqual(agent.id, 2)
        self.assertEqual(agent.position, (5, 10))
        self.assertEqual(agent.energy, 150)
        self.assertEqual(agent.age, 0)
        self.assertTrue(agent.alive)


class TestAgentTick(unittest.TestCase):
    """Test Agent tick lifecycle method"""
    
    def test_tick_increases_age(self):
        """Test that tick increases agent age"""
        agent = Agent(agent_id=1, position=(0, 0))
        agent.tick()
        self.assertEqual(agent.age, 1)
        agent.tick()
        self.assertEqual(agent.age, 2)
    
    def test_tick_decreases_energy(self):
        """Test that tick decreases agent energy"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
        agent.tick()
        self.assertEqual(agent.energy, 99)
        agent.tick()
        self.assertEqual(agent.energy, 98)
    
    def test_tick_kills_agent_at_zero_energy(self):
        """Test that agent dies when energy reaches zero"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=1)
        self.assertTrue(agent.alive)
        agent.tick()
        self.assertFalse(agent.alive)
        self.assertEqual(agent.energy, 0)
    
    def test_tick_does_nothing_when_dead(self):
        """Test that tick does nothing when agent is already dead"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=1)
        agent.tick()  # Dies
        self.assertFalse(agent.alive)
        
        # Additional ticks should not change state
        age_before = agent.age
        energy_before = agent.energy
        agent.tick()
        self.assertEqual(agent.age, age_before)
        self.assertEqual(agent.energy, energy_before)
        self.assertFalse(agent.alive)


class TestAgentDeath(unittest.TestCase):
    """Test Agent death mechanism"""
    
    def test_die_sets_alive_to_false(self):
        """Test that die method sets alive to False"""
        agent = Agent(agent_id=1, position=(0, 0))
        self.assertTrue(agent.alive)
        agent.die()
        self.assertFalse(agent.alive)
    
    def test_die_can_be_called_multiple_times(self):
        """Test that die method can be called multiple times safely"""
        agent = Agent(agent_id=1, position=(0, 0))
        agent.die()
        agent.die()
        self.assertFalse(agent.alive)


class TestAgentReproduction(unittest.TestCase):
    """Test Agent reproduction lifecycle"""
    
    def test_can_reproduce_when_mature_and_energetic(self):
        """Test that agent can reproduce when conditions are met"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=REPRODUCTION_ENERGY_THRESHOLD)
        agent.age = MATURITY_AGE
        self.assertTrue(agent.can_reproduce())
    
    def test_cannot_reproduce_when_too_young(self):
        """Test that young agents cannot reproduce"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=REPRODUCTION_ENERGY_THRESHOLD)
        agent.age = MATURITY_AGE - 1
        self.assertFalse(agent.can_reproduce())
    
    def test_cannot_reproduce_with_low_energy(self):
        """Test that agents with low energy cannot reproduce"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=REPRODUCTION_ENERGY_THRESHOLD - 1)
        agent.age = MATURITY_AGE
        self.assertFalse(agent.can_reproduce())
    
    def test_cannot_reproduce_when_dead(self):
        """Test that dead agents cannot reproduce"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=REPRODUCTION_ENERGY_THRESHOLD)
        agent.age = MATURITY_AGE
        agent.die()
        self.assertFalse(agent.can_reproduce())
    
    def test_reproduce_creates_offspring(self):
        """Test that reproduce method creates an offspring"""
        agent = Agent(agent_id=1, position=(5, 5), initial_energy=REPRODUCTION_ENERGY_THRESHOLD)
        agent.age = MATURITY_AGE
        
        offspring = agent.reproduce(new_agent_id=2)
        
        self.assertIsNotNone(offspring)
        self.assertIsInstance(offspring, Agent)
        self.assertEqual(offspring.id, 2)
        self.assertEqual(offspring.position, (5, 5))
        self.assertEqual(offspring.energy, 50)
        self.assertEqual(offspring.age, 0)
        self.assertTrue(offspring.alive)
    
    def test_reproduce_costs_energy(self):
        """Test that reproduction costs parent energy"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=REPRODUCTION_ENERGY_THRESHOLD)
        agent.age = MATURITY_AGE
        initial_energy = agent.energy
        
        agent.reproduce(new_agent_id=2)
        
        self.assertEqual(agent.energy, initial_energy - 50)
    
    def test_reproduce_returns_none_when_cannot_reproduce(self):
        """Test that reproduce returns None when conditions not met"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=50)
        agent.age = MATURITY_AGE - 1  # Too young
        
        offspring = agent.reproduce(new_agent_id=2)
        
        self.assertIsNone(offspring)


class TestAgentEating(unittest.TestCase):
    """Test Agent eating and energy management"""
    
    def test_eat_increases_energy(self):
        """Test that eating increases agent energy"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
        agent.eat(food_energy=20)
        self.assertEqual(agent.energy, 120)
    
    def test_eat_with_custom_food_energy(self):
        """Test eating with different food energy values"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
        agent.eat(food_energy=30)
        self.assertEqual(agent.energy, 130)
    
    def test_eat_caps_energy_at_200(self):
        """Test that energy is capped at 200"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=190)
        agent.eat(food_energy=20)
        self.assertEqual(agent.energy, 200)
    
    def test_eat_with_energy_over_cap(self):
        """Test eating when energy would exceed cap"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=195)
        agent.eat(food_energy=50)
        self.assertEqual(agent.energy, 200)


class TestAgentMovement(unittest.TestCase):
    """Test Agent movement"""
    
    def test_move_updates_position(self):
        """Test that move updates agent position"""
        agent = Agent(agent_id=1, position=(0, 0))
        agent.move((5, 10))
        self.assertEqual(agent.position, (5, 10))
    
    def test_move_multiple_times(self):
        """Test multiple moves"""
        agent = Agent(agent_id=1, position=(0, 0))
        agent.move((1, 1))
        self.assertEqual(agent.position, (1, 1))
        agent.move((2, 3))
        self.assertEqual(agent.position, (2, 3))


class TestAgentLifecycleIntegration(unittest.TestCase):
    """Integration tests for complete agent lifecycle"""
    
    def test_complete_lifecycle_until_death(self):
        """Test agent lifecycle from birth to death"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=5)
        
        # Agent starts alive
        self.assertTrue(agent.alive)
        self.assertEqual(agent.age, 0)
        
        # Age the agent
        for i in range(4):
            agent.tick()
            self.assertTrue(agent.alive)
            self.assertEqual(agent.age, i + 1)
        
        # Final tick should kill the agent
        agent.tick()
        self.assertFalse(agent.alive)
        self.assertEqual(agent.energy, 0)
    
    def test_lifecycle_with_eating_and_reproduction(self):
        """Test agent lifecycle with eating and reproduction"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
        
        # Age agent to maturity
        for _ in range(MATURITY_AGE):
            agent.tick()
        
        self.assertEqual(agent.age, MATURITY_AGE)
        self.assertEqual(agent.energy, 100 - MATURITY_AGE)
        
        # Feed agent to reproduction threshold
        food_needed = REPRODUCTION_ENERGY_THRESHOLD - agent.energy
        agent.eat(food_energy=food_needed)
        
        # Agent should be able to reproduce now
        self.assertTrue(agent.can_reproduce())
        
        # Reproduce
        offspring = agent.reproduce(new_agent_id=2)
        self.assertIsNotNone(offspring)
        self.assertEqual(offspring.id, 2)
        self.assertTrue(offspring.alive)
        self.assertEqual(offspring.energy, 50)
    
    def test_move_and_tick_interaction(self):
        """Test that movement and tick work together"""
        agent = Agent(agent_id=1, position=(0, 0), initial_energy=100)
        
        agent.move((5, 5))
        agent.tick()
        
        self.assertEqual(agent.position, (5, 5))
        self.assertEqual(agent.age, 1)
        self.assertEqual(agent.energy, 99)
        self.assertTrue(agent.alive)


if __name__ == '__main__':
    unittest.main()
