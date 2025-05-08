"""
Status panel for the Agent Survival Simulation.

The StatusPanel class is responsible for displaying information about the
current state of the active agent and the world, including energy levels,
statistics, and other relevant data.
"""
import pygame
from config import (
    WORLD_SIZE, COLOR, CELL_SIZE, SCREEN_WIDTH, VIEWPORT_HEIGHT,
    CALORIE_CONSUMPTION_PER_DAY, MOVES_PER_DAY, STATUS_PANEL_HEIGHT
)

class StatusPanel:
    """
    Displays statistics and status information about the agent and simulation.
    
    The StatusPanel renders a UI element at the bottom of the screen that shows
    information about the active agent's status, energy levels, and world statistics.
    It organizes this information into logical sections for better readability.
    """
    
    def __init__(self):
        """
        Initialize the status panel.
        """
        self.height = STATUS_PANEL_HEIGHT
        self.y_position = VIEWPORT_HEIGHT * CELL_SIZE  # Position below the viewport
        
        # Initialize fonts
        self._initialize_fonts()
        
        # Define sections of the panel
        self._initialize_layout()
        
        # Cached surfaces for performance
        self._cached_surfaces = {}
    
    def _initialize_fonts(self):
        """Initialize fonts used by the status panel."""
        self.title_font = pygame.font.SysFont('Arial', 18, bold=True)
        self.font = pygame.font.SysFont('Arial', 16)
        self.small_font = pygame.font.SysFont('Arial', 14)
    
    def _initialize_layout(self):
        """Initialize the layout of the status panel sections."""
        self.layout = {
            'agent_info': {
                'x': 20,
                'y': 10,
                'width': SCREEN_WIDTH // 2 - 30,
                'height': 100
            },
            'energy_bars': {
                'x': SCREEN_WIDTH // 2 + 20,
                'y': 10,
                'width': SCREEN_WIDTH // 2 - 30,
                'height': 100
            },
            'world_info': {
                'x': 20,
                'y': 110,
                'width': SCREEN_WIDTH - 40,
                'height': 30
            },
            'help': {
                'x': SCREEN_WIDTH // 4,
                'y': self.height - 25,
                'width': SCREEN_WIDTH // 2,
                'height': 20
            }
        }
    
    def draw(self, screen, agent, turns, is_day, world=None):
        """
        Draw the status panel with agent information.
        
        Args:
            screen: The pygame screen to draw on.
            agent (Agent): The agent to display information about.
            turns (int): The current turn count.
            is_day (bool): Whether it is currently day or night.
            world (World): The world object for additional stats.
        """
        # Draw background
        self._draw_background(screen)
        
        # Draw sections
        self._draw_agent_info(screen, agent)
        self._draw_energy_bars(screen, agent)
        
        if world:
            self._draw_world_info(screen, world, turns, is_day)
            
        self._draw_help_text(screen)
    
    def _draw_background(self, screen):
        """Draw the panel background with sections and dividers."""
        # Main panel background
        panel_rect = pygame.Rect(0, self.y_position, SCREEN_WIDTH, self.height)
        pygame.draw.rect(screen, COLOR['GRAY'], panel_rect)
        
        # Divider lines
        divider_color = (100, 100, 100)  # Darker gray for dividers
        
        # Vertical divider
        pygame.draw.line(
            screen, divider_color, 
            (SCREEN_WIDTH // 2, self.y_position),
            (SCREEN_WIDTH // 2, self.y_position + 110), 
            2
        )
                       
        # Horizontal divider
        pygame.draw.line(
            screen, divider_color, 
            (0, self.y_position + 110),
            (SCREEN_WIDTH, self.y_position + 110), 
            2
        )
    
    def _draw_agent_info(self, screen, agent):
        """Draw agent information on the left side."""
        section = self.layout['agent_info']
        x, y = section['x'], self.y_position + section['y']
        
        # Agent ID with colored indicator
        agent_color = self._get_agent_color(agent)
        
        # Draw color indicator
        indicator_size = 14
        pygame.draw.rect(
            screen, 
            agent_color,
            pygame.Rect(x, y + 3, indicator_size, indicator_size)
        )
        
        # Title with agent ID
        title = self.title_font.render(f"AGENT: {agent.agent_id}", True, COLOR['BLACK'])
        screen.blit(title, (x + indicator_size + 10, y))
        
        # Agent stats
        stats = [
            self._format_position(agent),
            self._format_status(agent),
            self._format_days_survived(agent),
            self._format_moves_today(agent)
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, COLOR['BLACK'])
            screen.blit(text, (x, y + 30 + i * 20))
    
    def _format_position(self, agent):
        """Format the agent position text."""
        return f"Position: ({agent.x}, {agent.y})"
    
    def _format_status(self, agent):
        """Format the agent status text."""
        if not agent.alive:
            return "Status: Dead"
        elif agent.is_sleeping:
            return "Status: Sleeping"
        else:
            return "Status: Awake"
    
    def _format_days_survived(self, agent):
        """Format the days survived text."""
        return f"Days Survived: {agent.days_survived}"
    
    def _format_moves_today(self, agent):
        """Format the moves today text."""
        if agent.is_sleeping:
            return f"Sleep Progress: {int((agent.sleep_energy / agent.max_sleep_energy) * 100)}%"
        else:
            return f"Moves Today: {agent.moves_today}/{MOVES_PER_DAY}"
    
    def _get_agent_color(self, agent):
        """Get the current color for the agent based on its state."""
        from config import AGENT_COLORS
        
        if not agent.alive:
            return (150, 150, 150)  # Gray for dead
        elif agent.is_sleeping:
            return AGENT_COLORS[agent.agent_id]['asleep']
        else:
            return AGENT_COLORS[agent.agent_id]['awake']
    
    def _draw_energy_bars(self, screen, agent):
        """Draw energy bars on the right side."""
        section = self.layout['energy_bars']
        x, y = section['x'], self.y_position + section['y']
        
        # Title
        title = self.title_font.render("ENERGY LEVELS", True, COLOR['BLACK'])
        screen.blit(title, (x, y))
        
        # Bar settings
        bar_width = 180
        bar_height = 15
        bar_x = x + 100
        
        # Stored calories bar
        cal_y = y + 30
        self._draw_bar(
            screen, "Stored:", bar_x, cal_y, bar_width, bar_height, 
            agent.calories / agent.max_calories, COLOR['RED'],
            f"{agent.calories}/{agent.max_calories}"
        )
        
        # Sleep energy bar
        sleep_y = y + 55
        self._draw_bar(
            screen, "Sleep:", bar_x, sleep_y, bar_width, bar_height, 
            agent.sleep_energy / agent.max_sleep_energy, COLOR['BLUE'],
            f"{agent.sleep_energy}/{agent.max_sleep_energy}"
        )
        
        # Collected calories bar
        collected_y = y + 80
        self._draw_bar(
            screen, "Collected:", bar_x, collected_y, bar_width, bar_height, 
            agent.collected_calories / agent.max_calories, (0, 180, 0),
            f"{agent.collected_calories}"
        )
        
        # Draw daily need indicator line on the collected bar
        daily_need = CALORIE_CONSUMPTION_PER_DAY / agent.max_calories
        need_x = bar_x + (bar_width * daily_need)
        pygame.draw.line(
            screen, COLOR['RED'], 
            (need_x, collected_y),
            (need_x, collected_y + bar_height), 
            2
        )
    
    def _draw_bar(self, screen, label, x, y, width, height, fill_percent, color, value_text=""):
        """
        Draw a labeled bar with fill percentage and value.
        
        Args:
            screen: The pygame screen to draw on.
            label: Text label for the bar.
            x, y: Position coordinates.
            width, height: Dimensions of the bar.
            fill_percent: How full the bar should be (0.0 to 1.0).
            color: Color of the fill.
            value_text: Optional text showing the value.
        """
        # Draw label
        label_surf = self.font.render(label, True, COLOR['BLACK'])
        screen.blit(label_surf, (x - 90, y))
        
        # Draw outline
        outline_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, COLOR['BLACK'], outline_rect, 1)
        
        # Draw fill
        fill_width = max(0, int(width * fill_percent))
        fill_rect = pygame.Rect(x, y, fill_width, height)
        pygame.draw.rect(screen, color, fill_rect)
        
        # Draw value text if provided
        if value_text:
            value_surf = self.font.render(value_text, True, COLOR['BLACK'])
            screen.blit(value_surf, (x + width + 10, y))
    
    def _draw_world_info(self, screen, world, turns, is_day):
        """Draw world information at the bottom."""
        section = self.layout['world_info']
        x, y = section['x'], self.y_position + section['y']
        
        # Time of day
        time_text = self.title_font.render(
            f"TIME: {'DAY' if is_day else 'NIGHT'}", 
            True, COLOR['BLACK']
        )
        screen.blit(time_text, (x, y))
        
        # Turn counter
        turn_text = self.font.render(f"Turn: {turns}", True, COLOR['BLACK'])
        screen.blit(turn_text, (x + 180, y))
        
        # World resources
        cell_counts = world.count_cells_by_state()
        resources_text = self.font.render(
            f"Resources: {cell_counts['full']} Full | {cell_counts['regrowing']} Regrowing | {cell_counts['consumed']} Consumed", 
            True, COLOR['BLACK']
        )
        screen.blit(resources_text, (x + 300, y))
    
    def _draw_help_text(self, screen):
        """Draw help text at the bottom."""
        section = self.layout['help']
        x, y = section['x'], self.y_position + section['y']
        
        help_text = self.font.render(
            "Press TAB to switch agents | SPACE to pause | R to restart", 
            True, COLOR['BLACK']
        )
        screen.blit(help_text, (x, y))
    
    def set_position(self, y_position):
        """
        Set the vertical position of the status panel.
        
        Args:
            y_position (int): The y-coordinate of the top of the panel.
        """
        self.y_position = y_position
    
    def clear_cache(self):
        """Clear any cached surfaces to free memory."""
        self._cached_surfaces.clear()