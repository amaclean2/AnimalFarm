"""
Time system for the Agent Survival Simulation.

The TimeSystem class manages the day/night cycle in the simulation, coordinating
transitions based on agent activities and maintaining time-related state.
"""
from config import MOVES_PER_DAY

class TimeSystem:
    """
    Manages the day/night cycle in the simulation.
    
    The TimeSystem class handles transitions between day and night based on
    agent activities. During the day, agents move and collect resources.
    During the night, agents sleep and consume their collected resources.
    """
    
    # Time state constants
    STATE_DAY = 0
    STATE_NIGHT = 1
    
    def __init__(self):
        """
        Initialize the time system.
        """
        self.is_day = True
        self.current_state = self.STATE_DAY
        self.day_count = 0
        self.time_cycles = 0  # Counter for total day/night cycles
    
    def update(self, agents):
        """
        Update the time of day based on agent actions.
        
        This method checks if conditions are met for transitioning between
        day and night, and updates the time state accordingly.
        
        Args:
            agents: List of agents whose actions determine time progression.
            
        Returns:
            bool: True if the time changed (day to night or night to day), False otherwise.
        """
        living_agents = self._get_living_agents(agents)
        
        # If no agents are alive, don't change time
        if not living_agents:
            return False
        
        if self.is_day:
            return self._check_day_to_night_transition(living_agents)
        else:
            return self._check_night_to_day_transition(living_agents)
    
    def _get_living_agents(self, agents):
        """Get a list of only living agents."""
        return [agent for agent in agents if agent.alive]
    
    def _check_day_to_night_transition(self, living_agents):
        """
        Check if conditions are met to transition from day to night.
        
        Transition occurs when all living agents have made their daily moves.
        
        Args:
            living_agents: List of living agents to check.
            
        Returns:
            bool: True if transition occurred, False otherwise.
        """
        # Check if all agents have made their daily moves
        all_agents_done = all(agent.moves_today >= MOVES_PER_DAY for agent in living_agents)
        
        if all_agents_done:
            self._transition_to_night()
            return True
            
        return False
    
    def _check_night_to_day_transition(self, living_agents):
        """
        Check if conditions are met to transition from night to day.
        
        Transition occurs when all living agents have finished sleeping.
        
        Args:
            living_agents: List of living agents to check.
            
        Returns:
            bool: True if transition occurred, False otherwise.
        """
        # Check if all agents have finished sleeping
        all_agents_awake = all(not agent.is_sleeping for agent in living_agents)
        
        if all_agents_awake:
            self._transition_to_day()
            return True
            
        return False
    
    def _transition_to_night(self):
        """
        Transition from day to night.
        
        Updates state, increments cycle counter, and logs the transition.
        """
        self.is_day = False
        self.current_state = self.STATE_NIGHT
        self.time_cycles += 1
        print("Night falls...")
    
    def _transition_to_day(self):
        """
        Transition from night to day.
        
        Updates state, increments cycle and day counters, and logs the transition.
        """
        self.is_day = True
        self.current_state = self.STATE_DAY
        self.time_cycles += 1
        self.day_count += 1
        print(f"A new day begins... (Day {self.day_count})")
    
    def get_day_progress(self, agents):
        """
        Calculate how far through the current day the simulation is.
        
        This can be used for visual indicators of day/night progression.
        
        Args:
            agents: List of agents to check.
            
        Returns:
            float: A value from 0.0 to 1.0 representing progress through the current phase.
        """
        living_agents = self._get_living_agents(agents)
        
        if not living_agents:
            return 0.0
        
        if self.is_day:
            # During day, track moves made
            avg_moves = sum(agent.moves_today for agent in living_agents) / len(living_agents)
            return min(1.0, avg_moves / MOVES_PER_DAY)
        else:
            # During night, track sleep progress
            avg_sleep_pct = sum(agent.sleep_energy / agent.max_sleep_energy 
                              for agent in living_agents) / len(living_agents)
            return avg_sleep_pct
    
    def get_current_time_description(self):
        """
        Get a descriptive string of the current time state.
        
        Returns:
            str: Description of the current time of day.
        """
        if self.is_day:
            return f"Day {self.day_count}"
        else:
            return f"Night {self.day_count}"
    
    def get_cycle_statistics(self):
        """
        Get statistics about the time cycles.
        
        Returns:
            dict: Dictionary containing time-related statistics.
        """
        return {
            'total_cycles': self.time_cycles,
            'days_passed': self.day_count,
            'current_state': 'Day' if self.is_day else 'Night',
            'current_day': self.day_count
        }