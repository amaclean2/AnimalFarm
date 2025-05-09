"""
Renderer for the Agent Survival Simulation.

The Renderer class is responsible for orchestrating all visual elements
of the simulation, including the world, agents, UI components, and special effects.
It handles the drawing order, camera management, and visual state transitions.
"""
import pygame
from config import COLOR, SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE
from visualization.status_panel import StatusPanel
from visualization.game_ui import GameUI
from visualization.camera import Camera

class Renderer:
    """
    Handles all rendering for the simulation.
    
    The Renderer coordinates drawing the world, agents, UI elements, and special
    effects in the correct order and with proper visual state handling.
    """
    
    # Game state constants to match those in the Game class
    STATE_RUNNING = 0
    STATE_PAUSED = 1
    STATE_GAME_OVER = 2
    
    def __init__(self):
        """
        Initialize the renderer.
        """
        self.status_panel = StatusPanel()
        self.game_ui = GameUI()
        self.camera = Camera()
        
        # Visual effects settings
        self.enable_visual_effects = True
        self.show_debug_info = False
        
        # Frame tracking for animations
        self.frame_count = 0
        
        # Visual effect surfaces
        self._weather_overlay = None
        self._light_level = 1.0  # 0.0 = dark, 1.0 = full brightness
    
    def render_frame(self, screen, world, agents, active_agent_index, is_day, turns, game_state, home_base=None):
        """
        Render a complete frame of the simulation.
        
        Args:
            screen: The pygame screen to draw on.
            world: The world to render.
            agents: List of all agents in the simulation.
            active_agent_index: Index of the currently active agent.
            is_day (bool): Whether it is currently day or night.
            turns (int): The current turn count.
            game_state: The current state of the game (running, paused, game over).
            home_base (tuple): Optional (x, y) coordinates of the home base.
        """
        # Increment frame counter for animations
        self.frame_count += 1
        
        # Periodically output debug info if enabled
        self._output_debug_info(agents, active_agent_index, turns)
        
        # Get active agent for camera following
        active_agent = self._get_active_agent(agents, active_agent_index)
        
        # Clear the screen with appropriate background color
        self._fill_background(screen, is_day)
        
        # Draw the world
        self._draw_world(screen, world, is_day)
        
        # Draw home base if provided
        if home_base:
            self._draw_home_base(screen, home_base, is_day)
        
        # Draw all agents
        self._draw_agents(screen, agents, active_agent_index)
        
        # Draw environmental effects
        if self.enable_visual_effects:
            self._draw_environmental_effects(screen, is_day)
        
        # Draw UI elements based on game state
        self._draw_ui_elements(screen, world, agents, active_agent, turns, is_day, game_state, home_base)
        
        # Draw debug info if enabled
        if self.show_debug_info:
            self._draw_debug_info(screen, world, agents, active_agent, turns, home_base)
        
        # Update the display
        pygame.display.flip()
    
    def _output_debug_info(self, agents, active_agent_index, turns):
        """Output debug information periodically to the console."""
        if self.show_debug_info and turns % 500 == 0:
            print(f"Rendering frame: {len(agents)} agents, active index: {active_agent_index}")
            for i, agent in enumerate(agents):
                print(f"  Agent {i+1}: {agent.agent_id} at ({agent.x}, {agent.y}), alive: {agent.alive}")
    
    def _get_active_agent(self, agents, active_agent_index):
        """Get the active agent, ensuring the index is valid."""
        if agents and 0 <= active_agent_index < len(agents):
            return agents[active_agent_index]
        return None
    
    def _fill_background(self, screen, is_day):
        """Fill the screen with the appropriate background color."""
        bg_color = COLOR['WHITE'] if is_day else COLOR['DARK_BLUE']
        screen.fill(bg_color)
    
    def _draw_world(self, screen, world, is_day):
        """Draw the world using the camera."""
        world.draw(screen, night_mode=not is_day, camera=self.camera)
    
    def _draw_home_base(self, screen, home_base, is_day):
        """
        Draw the home base on the screen.
        
        Args:
            screen: The pygame screen to draw on.
            home_base (tuple): (x, y) coordinates of the home base.
            is_day (bool): Whether it is currently day or night.
        """
        home_x, home_y = home_base
        
        # Check if home base is visible on screen
        if not self.camera.is_visible(home_x, home_y):
            return
            
        # Convert world coordinates to screen coordinates
        screen_pos = self.camera.world_to_screen(home_x, home_y)
        if not screen_pos:
            return
            
        # Calculate pixel position
        center_x = screen_pos[0] * CELL_SIZE + CELL_SIZE // 2
        center_y = screen_pos[1] * CELL_SIZE + CELL_SIZE // 2
        
        # Draw home base with a distinctive marker
        base_radius = CELL_SIZE // 2
        base_color = COLOR['YELLOW'] if is_day else (200, 200, 100)  # Yellowish color
        
        # Draw outer circle
        pygame.draw.circle(screen, base_color, (center_x, center_y), base_radius, 3)
        
        # Draw inner cross
        pygame.draw.line(screen, base_color, 
                        (center_x - base_radius//2, center_y), 
                        (center_x + base_radius//2, center_y), 
                        2)
        pygame.draw.line(screen, base_color, 
                        (center_x, center_y - base_radius//2), 
                        (center_x, center_y + base_radius//2), 
                        2)
    
    def _draw_agents(self, screen, agents, active_agent_index):
        """Draw all agents and ghost indicators for dead agents."""
        # Count living agents and draw them
        living_agents = 0
        for agent in agents:
            if agent.alive:
                living_agents += 1
                agent.draw(screen, camera=self.camera)
        
        # Draw "ghost" for dead agents that are being viewed
        if active_agent_index < len(agents) and not agents[active_agent_index].alive:
            dead_agent = agents[active_agent_index]
            self._draw_ghost_agent(screen, dead_agent)
    
    def _draw_ghost_agent(self, screen, agent):
        """Draw a ghostly version of a dead agent."""
        # Only draw if in camera view
        if not self.camera.is_visible(agent.x, agent.y):
            return
            
        # Get screen position
        screen_pos = self.camera.world_to_screen(agent.x, agent.y)
        if not screen_pos:
            return
            
        # Calculate pixel position
        center_x = screen_pos[0] * CELL_SIZE + CELL_SIZE // 2
        center_y = screen_pos[1] * CELL_SIZE + CELL_SIZE // 2
        radius = CELL_SIZE // 2 - 4
        
        # Create ghostly circle
        ghost_color = (200, 200, 200, 150)  # Semi-transparent light gray
        ghost_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(ghost_surface, ghost_color, (radius, radius), radius)
        
        # Add X mark
        line_color = (100, 100, 100, 200)
        pygame.draw.line(ghost_surface, line_color, (radius-5, radius-5), (radius+5, radius+5), 2)
        pygame.draw.line(ghost_surface, line_color, (radius-5, radius+5), (radius+5, radius-5), 2)
        
        # Draw ghost
        screen.blit(ghost_surface, (center_x - radius, center_y - radius))
    
    def _draw_environmental_effects(self, screen, is_day):
        """Draw environmental effects like weather and lighting."""
        # Currently no weather effects implemented
        # This is a placeholder for future expansion
        pass
    
    def _draw_ui_elements(self, screen, world, agents, active_agent, turns, is_day, game_state, home_base=None):
        """Draw all UI elements based on the current game state."""
        
        # Draw status panel for the active agent
        if active_agent:
            self.status_panel.draw(screen, active_agent, turns, is_day, world, home_base)
        
        # Draw state-dependent UI
        if game_state == self.STATE_PAUSED:
            self.game_ui.draw_pause_menu(screen)
        elif game_state == self.STATE_GAME_OVER:
            # Find the agent that survived the longest
            if agents:
                best_agent = max(agents, key=lambda a: a.days_survived)
                self.game_ui.draw_game_over(screen, best_agent)
    
    def _draw_debug_info(self, screen, world, agents, active_agent, turns, home_base=None):
        """Draw debug information on screen."""
        debug_lines = [
            f"FPS: {int(pygame.time.Clock().get_fps())}",
            f"Frame: {self.frame_count}",
            f"Turns: {turns}",
            f"Agents: {len(agents)} ({sum(1 for a in agents if a.alive)} alive)",
        ]
        
        if active_agent:
            debug_lines.append(f"Active Agent: {active_agent.agent_id} at ({active_agent.x},{active_agent.y})")
        
        if home_base:
            debug_lines.append(f"Home Base: ({home_base[0]}, {home_base[1]})")
        
        # Additional world stats
        cell_stats = world.count_cells_by_state()
        debug_lines.append(f"Cells: {cell_stats['full']} full, {cell_stats['regrowing']} regrowing")
        
        # Draw debug text
        font = pygame.font.SysFont('Courier', 14)
        for i, line in enumerate(debug_lines):
            text = font.render(line, True, (255, 255, 0))
            screen.blit(text, (10, 10 + i * 20))
    
    def set_camera_smoothing(self, smoothing):
        """Set the camera movement smoothing factor."""
        self.camera.set_smoothing(smoothing)
    
    def toggle_visual_effects(self):
        """Toggle visual effects on/off."""
        self.enable_visual_effects = not self.enable_visual_effects
        return self.enable_visual_effects
    
    def toggle_debug_info(self):
        """Toggle debug information display on/off."""
        self.show_debug_info = not self.show_debug_info
        return self.show_debug_info