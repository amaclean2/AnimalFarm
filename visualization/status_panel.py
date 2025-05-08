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
        # Panel dimensions
        panel_width = SCREEN_WIDTH
        
        # Fixed margins and spacing
        left_margin = 40
        right_margin = 40
        
        # Calculate column widths
        col_width = (panel_width - left_margin - right_margin) // 2
        
        # Layout sections
        self.layout = {
            'agent_info': {
                'x': left_margin,
                'y': 20,  # More vertical space at top
                'width': col_width,
                'height': 140
            },
            'energy_bars': {
                'x': left_margin + col_width + 40,  # More padding between columns
                'y': 20,
                'width': col_width - 40,  # Adjust for padding
                'height': 140
            },
            'world_info': {
                'x': left_margin,
                'y': 170,  # More space between sections
                'width': panel_width - left_margin - right_margin,
                'height': 40
            },
            'help': {
                'x': 0,  # Will be centered
                'y': self.height - 35,  # More space at bottom
                'width': panel_width,
                'height': 25
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
    
    def _draw_agent_info(self, screen, agent):
        """Draw agent information on the left side."""
        section = self.layout['agent_info']
        base_x, base_y = section['x'], self.y_position + section['y']
        
        # Agent ID with colored indicator
        agent_color = self._get_agent_color(agent)
        
        # Draw color indicator
        indicator_size = 16  # Slightly larger
        pygame.draw.rect(
            screen, 
            agent_color,
            pygame.Rect(base_x, base_y + 3, indicator_size, indicator_size)
        )
        
        # Title with agent ID
        title = self.title_font.render(f"AGENT: {agent.agent_id}", True, COLOR['BLACK'])
        screen.blit(title, (base_x + indicator_size + 12, base_y))
        
        # Agent stats with consistent spacing
        line_height = 25  # Increased line height
        stats_y_start = base_y + 35  # More space after title
        
        stats = [
            self._format_position(agent),
            self._format_status(agent),
            self._format_days_survived(agent),
            self._format_moves_today(agent)
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, COLOR['BLACK'])
            screen.blit(text, (base_x, stats_y_start + i * line_height))
    
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
        base_x, base_y = section['x'], self.y_position + section['y']
        
        # Title
        title = self.title_font.render("ENERGY LEVELS", True, COLOR['BLACK'])
        title_rect = title.get_rect(topleft=(base_x, base_y))
        screen.blit(title, title_rect)
        
        # Fixed dimensions for layout elements
        label_width = 90  # Wider to accommodate "Collected:"
        bar_width = 240   # Longer bars for better visibility
        bar_height = 18   # Taller bars
        value_padding = 15
        
        # Y positions for each bar with more spacing
        y_positions = [base_y + 35, base_y + 65, base_y + 95]
        
        # Draw each bar with consistent positioning
        self._draw_energy_bar(
            screen, "Stored:", base_x, y_positions[0], 
            label_width, bar_width, bar_height, value_padding,
            agent.calories, agent.max_calories, COLOR['RED']
        )
        
        self._draw_energy_bar(
            screen, "Sleep:", base_x, y_positions[1], 
            label_width, bar_width, bar_height, value_padding,
            agent.sleep_energy, agent.max_sleep_energy, COLOR['BLUE']
        )
        
        self._draw_energy_bar(
            screen, "Collected:", base_x, y_positions[2], 
            label_width, bar_width, bar_height, value_padding,
            agent.collected_calories, agent.max_calories, COLOR['GREEN']
        )
        
        # Draw daily need indicator line on the collected bar
        bar_x = base_x + label_width
        need_x = bar_x + (bar_width * (CALORIE_CONSUMPTION_PER_DAY / agent.max_calories))
        pygame.draw.line(
            screen, COLOR['RED'], 
            (need_x, y_positions[2]),
            (need_x, y_positions[2] + bar_height), 
            2
        )
    
    def _draw_energy_bar(self, screen, label_text, x, y, label_width, bar_width, 
                        bar_height, value_padding, current, maximum, color):
        """
        Draw a single energy bar with label and value.
        
        Args:
            screen: The pygame screen to draw on.
            label_text: Text for the bar label.
            x, y: Base position coordinates.
            label_width: Width allocated for the label.
            bar_width: Width of the progress bar.
            bar_height: Height of the progress bar.
            value_padding: Padding between bar and value text.
            current: Current value.
            maximum: Maximum value.
            color: Bar fill color.
        """
        # Draw label with fixed width
        label = self.font.render(label_text, True, COLOR['BLACK'])
        screen.blit(label, (x, y + (bar_height - label.get_height()) // 2))  # Vertical centering
        
        # Calculate positions
        bar_x = x + label_width
        value_x = bar_x + bar_width + value_padding
        
        # Draw bar outline
        outline_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, COLOR['BLACK'], outline_rect, 1)
        
        # Draw bar fill
        fill_percent = current / maximum if maximum > 0 else 0
        fill_width = max(0, int(bar_width * fill_percent))
        fill_rect = pygame.Rect(bar_x, y, fill_width, bar_height)
        pygame.draw.rect(screen, color, fill_rect)
        
        # Draw value text
        value_text = f"{current}/{maximum}"
        value = self.font.render(value_text, True, COLOR['BLACK'])
        screen.blit(value, (value_x, y + (bar_height - value.get_height()) // 2))  # Vertical centering
    
    def _draw_world_info(self, screen, world, turns, is_day):
        """Draw world information at the bottom."""
        section = self.layout['world_info']
        base_x, base_y = section['x'], self.y_position + section['y']
        
        # Get cell counts for resources
        cell_counts = world.count_cells_by_state()
        
        # Create a multi-column layout with fixed widths
        time_x = base_x
        turn_x = base_x + 200
        resources_x = base_x + 400
        
        # Time of day
        time_text = self.title_font.render(
            f"TIME: {'DAY' if is_day else 'NIGHT'}", 
            True, COLOR['BLACK']
        )
        screen.blit(time_text, (time_x, base_y))
        
        # Turn counter
        turn_text = self.font.render(f"Turn: {turns}", True, COLOR['BLACK'])
        screen.blit(turn_text, (turn_x, base_y))
        
        # Resources - on one line with better spacing
        resources_text = f"Resources: {cell_counts['full']} Full | {cell_counts['regrowing']} Regrowing | {cell_counts['consumed']} Consumed"
        resources = self.font.render(resources_text, True, COLOR['BLACK'])
        screen.blit(resources, (resources_x, base_y))
    
    def _draw_help_text(self, screen):
        """Draw help text at the bottom."""
        section = self.layout['help']
        y = self.y_position + section['y']
        
        help_text = "Press TAB to switch agents | SPACE to pause | R to restart"
        text_surface = self.font.render(help_text, True, COLOR['BLACK'])
        
        # Center the text horizontally
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y + 10))
        screen.blit(text_surface, text_rect)
    
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