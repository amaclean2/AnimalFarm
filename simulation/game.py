"""
Game manager for the Agent Survival Simulation.

This module provides the Game class which serves as the central coordinator
for the entire simulation. It manages the game loop, state transitions,
and coordinates all other components of the simulation.
"""
import pygame
import sys
from config import WORLD_SIZE, FPS, NUM_AGENTS, HOME_BASE_POSITION
from models.world import World
from models.agent import Agent
from simulation.time_system import TimeSystem
from visualization.renderer import Renderer

class Game:
    """
    Manages the game state, controls the game loop, and handles user input.
    
    The Game class coordinates all other components of the simulation,
    including the world, agents, time system, and renderer. It also handles
    user input and maintains the game loop.
    """
    
    # Game state constants
    STATE_RUNNING = 0
    STATE_PAUSED = 1
    STATE_GAME_OVER = 2
    
    # Key mapping constants
    KEY_PAUSE = pygame.K_SPACE
    KEY_EXIT = pygame.K_ESCAPE
    KEY_RESTART = pygame.K_r
    KEY_SWITCH_AGENT = pygame.K_TAB
    
    def __init__(self, screen):
        """
        Initialize the game.
        
        Args:
            screen: The pygame screen to draw on.
        """
        # Core components
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.renderer = Renderer()
        self.time_system = TimeSystem()
        
        # Game state
        self.state = self.STATE_RUNNING
        self.running = True
        self.turns = 0
        self.active_agent_index = 0
        
        # Game settings
        self.agent_count = NUM_AGENTS
        self.debug_mode = False
        self.target_fps = FPS
        
        # Game entities
        self.world = None
        self.agents = []
        
        # Home base coordinates
        self.home_base_x, self.home_base_y = HOME_BASE_POSITION
        
        # Initialize the simulation
        self._initialize_game()
        
    def _initialize_game(self):
        """
        Initialize or reset the game state.
        Creates a new world and places agents.
        """
        # Create the world
        self.world = World()
        
        # Create the specified number of agents
        self._create_agents()
        
        # Reset game state
        self.state = self.STATE_RUNNING
        self.time_system.is_day = True
        self.turns = 0
        self.active_agent_index = 0
        
        print(f"Game started with {len(self.agents)} agents!")
        print(f"Home base established at ({self.home_base_x}, {self.home_base_y})")
    
    def _create_agents(self):
        """
        Create and position all agents at the home base.
        """
        from models.agent import Agent
        
        self.agents = []
        
        # Create the specified number of agents
        for i in range(self.agent_count):
            # All agents start at the home base
            agent_id = f"agent{i+1}"
            
            # Create the agent
            self.agents.append(Agent(self.home_base_x, self.home_base_y, agent_id))
        
        print(f"Created {len(self.agents)} agents at home base")
    
    def set_agent_count(self, count):
        """
        Set the number of agents in the simulation.
        
        This method should be called before the game starts.
        
        Args:
            count (int): The number of agents (1-4).
        """
        # Limit to valid range
        self.agent_count = max(1, min(4, count))
        
        # If game hasn't started yet, don't do anything else
        if not hasattr(self, 'agents'):
            return
            
        # If we have agents already, resize the list
        if len(self.agents) > self.agent_count:
            # Remove excess agents
            self.agents = self.agents[:self.agent_count]
        elif len(self.agents) < self.agent_count:
            # Need to add more agents
            current_count = len(self.agents)
            
            # Add missing agents at the home base
            for i in range(current_count, self.agent_count):
                agent_id = f"agent{i+1}"
                
                from models.agent import Agent
                self.agents.append(Agent(self.home_base_x, self.home_base_y, agent_id))
        
        # Reset active agent
        self.active_agent_index = 0
        print(f"Agent count set to {self.agent_count}")

    def set_debug_mode(self, debug_enabled):
        """
        Enable or disable debug mode.
        
        Args:
            debug_enabled (bool): Whether debug mode should be enabled.
        """
        self.debug_mode = debug_enabled
        
        # Set debug mode in renderer
        if hasattr(self, 'renderer'):
            self.renderer.show_debug_info = debug_enabled
        
        print(f"Debug mode {'enabled' if debug_enabled else 'disabled'}")

    def set_fps(self, fps):
        """
        Set the target frames per second.
        
        Args:
            fps (int): The target FPS.
        """
        from config import FPS
        self.target_fps = max(1, min(120, fps))  # Limit to reasonable range
        
        # Update config (this is a bit hacky but works for simple cases)
        import config
        config.FPS = self.target_fps
        
        print(f"Target FPS set to {self.target_fps}")
    
    def run(self):
        """
        Run the main game loop.
        
        This is the core method that drives the simulation forward. It handles
        the game loop, processes events, updates the state, and renders frames.
        
        Returns:
            int: Exit code (0 for normal exit).
        """
        while self.running:
            # Process events
            self._process_events()
            
            # Update game state
            self._update()
            
            # Render
            self._render()
            
            # Cap the frame rate
            self.clock.tick(self.target_fps)
        
        # Game is exiting, show final statistics
        self._print_final_stats()
        
        return 0  # Exit code
    
    def _process_events(self):
        """Process all pygame events and handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                self._handle_keypress(event.key)
    
    def _handle_keypress(self, key):
        """
        Handle keyboard input.
        
        Args:
            key: The pygame key code that was pressed.
        """
        if key == self.KEY_PAUSE:
            self._toggle_pause()
            
        elif key == self.KEY_EXIT:
            self.running = False
            
        elif key == self.KEY_RESTART:
            self._initialize_game()
            print("Game restarted!")
            
        elif key == self.KEY_SWITCH_AGENT:
            self._switch_active_agent()
    
    def _toggle_pause(self):
        """Toggle between paused and running states."""
        if self.state == self.STATE_RUNNING:
            self.state = self.STATE_PAUSED
            print("Game paused")
        else:
            self.state = self.STATE_RUNNING
            print("Game resumed")
    
    def _switch_active_agent(self):
        """Switch to the next living agent in the list."""
        living_agents = [i for i, agent in enumerate(self.agents) if agent.alive]
        
        if living_agents:
            # Find index of current active agent in living agents list
            try:
                current_index = living_agents.index(self.active_agent_index)
                # Move to next agent (wrapping around)
                next_index = (current_index + 1) % len(living_agents)
                self.active_agent_index = living_agents[next_index]
            except ValueError:
                # Current agent is dead, switch to first living agent
                self.active_agent_index = living_agents[0]
                
            agent_id = self.agents[self.active_agent_index].agent_id
            print(f"Switched to {agent_id}")
    
    def _update(self):
        """Update the game state for one frame."""
        # Skip updates if paused or game over
        if self.state != self.STATE_RUNNING:
            return
            
        # Update the world for regrowth
        self.world.update()
        
        # Update all living agents
        self._update_agents()
        
        # Check for time changes
        self._check_time_transition()
        
        # Update camera to follow active agent
        self._update_camera()
        
        # Update game state if all agents are dead
        if not any(agent.alive for agent in self.agents):
            self.state = self.STATE_GAME_OVER
        
        # Increment turn counter
        self.turns += 1
    
    def _update_agents(self):
        """Update all living agents based on time of day."""
        for agent in self.agents:
            if agent.alive:
                agent.update(self.world, self.time_system.is_day)
    
    def _check_time_transition(self):
        """Check if the time of day should change."""
        time_changed = self.time_system.update(self.agents)
        
        # Handle day-night transitions
        if time_changed:
            if self.time_system.is_day:
                # New day has begun, ensure active agent is alive
                self._ensure_active_agent_alive()
            else:
                # Night has begun, check which agents made it home
                self._check_agents_at_home()
    
    def _check_agents_at_home(self):
        """Check which agents successfully made it back to home base before nightfall."""
        for agent in self.agents:
            if agent.alive:
                if agent.is_at_home():
                    print(f"{agent.agent_id} made it back to home base!")
                else:
                    # Agent didn't make it back - they lose half their collected calories
                    penalty = agent.collected_calories // 2
                    agent.collected_calories -= penalty
                    print(f"{agent.agent_id} didn't make it home! Lost {penalty} calories.")
    
    def _ensure_active_agent_alive(self):
        """Make sure the active agent is a living one."""
        if not self.agents[self.active_agent_index].alive:
            living_agents = [i for i, agent in enumerate(self.agents) if agent.alive]
            
            if living_agents:
                self.active_agent_index = living_agents[0]
    
    def _update_camera(self):
        """Update the camera to follow the active agent."""
        if self.agents and 0 <= self.active_agent_index < len(self.agents):
            active_agent = self.agents[self.active_agent_index]
            self.renderer.camera.update(active_agent.x, active_agent.y)
    
    def _render(self):
        """Render the current game state to the screen."""
        self.renderer.render_frame(
            self.screen, 
            self.world, 
            self.agents,
            self.active_agent_index,
            self.time_system.is_day, 
            self.turns,
            self.state,
            (self.home_base_x, self.home_base_y)  # Pass home base coordinates
        )
    
    def _print_final_stats(self):
        """Print final game statistics to the console."""
        cell_stats = self.world.count_cells_by_state()
        
        print("\nFinal Statistics:")
        print("-----------------")
        
        # Agent statistics
        for i, agent in enumerate(self.agents):
            print(f"Agent {i+1} ({agent.agent_id}) survived for {agent.days_survived} days")
            print(f"  Total distance traveled: {agent.total_distance_traveled}")
            
        # World statistics
        print(f"\nWorld Status:")
        print(f"  Full cells: {cell_stats['full']} ({cell_stats['full_percent']:.1f}%)")
        print(f"  Regrowing cells: {cell_stats['regrowing']} ({cell_stats['regrowing_percent']:.1f}%)")
        print(f"  Consumed cells: {cell_stats['consumed']} ({cell_stats['consumed_percent']:.1f}%)")
        
        # Winner announcement
        if self.agents:
            best_agent = max(self.agents, key=lambda a: a.days_survived)
            print(f"\nWinner: {best_agent.agent_id} with {best_agent.days_survived} days survived")