"""
Game UI elements for the Agent Survival Simulation.

This module provides UI components for game-level displays such as the
game over screen, pause menu, and other full-screen overlays.
"""
import pygame
from config import COLOR, SCREEN_WIDTH, SCREEN_HEIGHT

class GameUI:
    """
    Handles UI elements like the game over screen, pause menu, and overlays.
    
    The GameUI class is responsible for rendering full-screen UI elements
    that provide game state information or prompt for user interaction.
    """
    
    def __init__(self):
        """
        Initialize the game UI.
        """
        # Initialize fonts
        self._initialize_fonts()
        
        # Cached surfaces for performance
        self._cached_surfaces = {}
    
    def _initialize_fonts(self):
        """Initialize fonts used by the UI elements."""
        self.title_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.subtitle_font = pygame.font.SysFont('Arial', 32, bold=True)
        self.medium_font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
    
    def draw_game_over(self, screen, agent):
        """
        Display game over message and statistics.
        
        Args:
            screen: The pygame screen to draw on.
            agent (Agent): The agent that survived the longest.
        """
        # Draw semi-transparent overlay
        self._draw_overlay(screen, alpha=180)
        
        # Draw game over content
        self._draw_game_over_title(screen)
        self._draw_winner_info(screen, agent)
        self._draw_death_info(screen, agent)
        self._draw_restart_instructions(screen)
    
    def _draw_overlay(self, screen, alpha=180):
        """
        Draw a semi-transparent overlay on the screen.
        
        Args:
            screen: The pygame screen to draw on.
            alpha (int): Transparency level (0-255).
        """
        # Create or get cached overlay surface
        overlay_key = f"overlay_{alpha}"
        if overlay_key not in self._cached_surfaces:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))  # Dark semi-transparent overlay
            self._cached_surfaces[overlay_key] = overlay
        
        screen.blit(self._cached_surfaces[overlay_key], (0, 0))
    
    def _draw_game_over_title(self, screen):
        """Draw the game over title."""
        # Create title with shadow effect
        game_over_text = self._render_text_with_shadow(
            "GAME OVER", self.title_font, COLOR['RED'], (0, 0, 0)
        )
        text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 80))
        screen.blit(game_over_text, text_rect)
    
    def _draw_winner_info(self, screen, agent):
        """Draw information about the winning agent."""
        # Winner text
        winner_text = self._render_text_with_shadow(
            f"{agent.agent_id} survived the longest", 
            self.medium_font, COLOR['WHITE'], (0, 0, 0)
        )
        winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
        screen.blit(winner_text, winner_rect)
        
        # Days survived
        days_text = self._render_text_with_shadow(
            f"Days survived: {agent.days_survived}", 
            self.medium_font, COLOR['WHITE'], (0, 0, 0)
        )
        days_rect = days_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(days_text, days_rect)
    
    def _draw_death_info(self, screen, agent):
        """Draw information about how the agent died."""
        # Determine death reason
        death_reason = "Starvation" if agent.calories <= 0 else "Exhaustion"
        
        # Death reason text
        death_text = self._render_text_with_shadow(
            f"Cause of death: {death_reason}", 
            self.medium_font, COLOR['WHITE'], (0, 0, 0)
        )
        death_rect = death_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30))
        screen.blit(death_text, death_rect)
    
    def _draw_restart_instructions(self, screen):
        """Draw instructions for restarting the game."""
        # Create pulsing effect for the restart text
        alpha = int(127 + 127 * abs(pygame.time.get_ticks() % 2000 / 1000 - 1))
        restart_text = self._render_text_with_alpha(
            "Press 'R' to restart", 
            self.medium_font, COLOR['WHITE'], alpha
        )
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 70))
        screen.blit(restart_text, restart_rect)
    
    def draw_pause_menu(self, screen):
        """
        Display the pause menu.
        
        Args:
            screen: The pygame screen to draw on.
        """
        # Draw semi-transparent overlay
        self._draw_overlay(screen, alpha=120)
        
        # Pause title
        pause_text = self._render_text_with_shadow(
            "PAUSED", self.title_font, COLOR['WHITE'], (0, 0, 0)
        )
        text_rect = pause_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        screen.blit(pause_text, text_rect)
        
        # Instructions
        instructions = [
            "Press SPACE to resume",
            "Press R to restart",
            "Press ESC to quit"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = self._render_text_with_shadow(
                instruction, self.medium_font, COLOR['WHITE'], (0, 0, 0)
            )
            inst_rect = inst_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + i * 30))
            screen.blit(inst_text, inst_rect)
    
    def draw_agent_dead_notice(self, screen):
        """
        Draw a notice that the current agent is dead.
        
        Args:
            screen: The pygame screen to draw on.
        """
        # Create semi-transparent overlay at the top of the screen
        overlay_height = 40
        overlay = pygame.Surface((SCREEN_WIDTH, overlay_height), pygame.SRCALPHA)
        overlay.fill((200, 0, 0, 150))  # Semi-transparent red
        screen.blit(overlay, (0, 0))
        
        # Add text
        text = self._render_text_with_shadow(
            "THIS AGENT IS DEAD - Press TAB to switch to a living agent",
            self.small_font, COLOR['WHITE'], (0, 0, 0)
        )
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, overlay_height//2))
        screen.blit(text, text_rect)
    
    def draw_day_night_indicator(self, screen, is_day, progress, day_count):
        """
        Draw an indicator showing the current time of day and progress.
        
        Args:
            screen: The pygame screen to draw on.
            is_day (bool): Whether it is currently day or night.
            progress (float): Progress through the current phase (0.0 to 1.0).
            day_count (int): The current day number.
        """
        # Indicator position and size
        indicator_width = 100
        indicator_height = 30
        indicator_x = SCREEN_WIDTH - indicator_width - 10
        indicator_y = 10
        
        # Draw background
        bg_color = COLOR['WHITE'] if is_day else COLOR['DARK_BLUE']
        bg_rect = pygame.Rect(indicator_x, indicator_y, indicator_width, indicator_height)
        pygame.draw.rect(screen, bg_color, bg_rect)
        pygame.draw.rect(screen, COLOR['BLACK'], bg_rect, 2)  # Border
        
        # Draw sun/moon icon
        icon_radius = indicator_height // 2 - 5
        icon_x = indicator_x + icon_radius + 5
        icon_y = indicator_y + indicator_height // 2
        
        if is_day:
            # Draw sun
            pygame.draw.circle(screen, COLOR['YELLOW'], (icon_x, icon_y), icon_radius)
        else:
            # Draw moon
            pygame.draw.circle(screen, COLOR['WHITE'], (icon_x, icon_y), icon_radius)
            # Draw shadow to create crescent
            shadow_x = icon_x - icon_radius // 3
            pygame.draw.circle(screen, bg_color, (shadow_x, icon_y), icon_radius * 0.8)
        
        # Draw text
        text = self.small_font.render(f"Day {day_count}", True, COLOR['BLACK'] if is_day else COLOR['WHITE'])
        text_rect = text.get_rect(center=(indicator_x + indicator_width * 0.7, indicator_y + indicator_height // 2))
        screen.blit(text, text_rect)
        
        # Draw progress bar below
        bar_height = 5
        bar_y = indicator_y + indicator_height + 2
        bar_bg_rect = pygame.Rect(indicator_x, bar_y, indicator_width, bar_height)
        bar_fill_rect = pygame.Rect(indicator_x, bar_y, indicator_width * progress, bar_height)
        
        pygame.draw.rect(screen, COLOR['GRAY'], bar_bg_rect)
        pygame.draw.rect(screen, COLOR['GREEN'] if is_day else COLOR['BLUE'], bar_fill_rect)
    
    def _render_text_with_shadow(self, text, font, color, shadow_color, shadow_offset=2):
        """
        Render text with a shadow effect.
        
        Args:
            text (str): The text to render.
            font: The pygame font to use.
            color: The color of the main text.
            shadow_color: The color of the shadow.
            shadow_offset (int): The offset of the shadow.
            
        Returns:
            Surface: A surface containing the rendered text with shadow.
        """
        # Cache key for this text rendering
        cache_key = f"text_{text}_{font.get_height()}_{color}_{shadow_color}_{shadow_offset}"
        
        # Return cached surface if available
        if cache_key in self._cached_surfaces:
            return self._cached_surfaces[cache_key]
        
        # Render shadow and main text
        shadow = font.render(text, True, shadow_color)
        text_surface = font.render(text, True, color)
        
        # Create a new surface to hold both
        combined = pygame.Surface(
            (text_surface.get_width() + shadow_offset, text_surface.get_height() + shadow_offset),
            pygame.SRCALPHA
        )
        
        # Blit shadow then text
        combined.blit(shadow, (shadow_offset, shadow_offset))
        combined.blit(text_surface, (0, 0))
        
        # Cache and return
        self._cached_surfaces[cache_key] = combined
        return combined
    
    def _render_text_with_alpha(self, text, font, color, alpha):
        """
        Render text with a specific alpha value.
        
        Args:
            text (str): The text to render.
            font: The pygame font to use.
            color: The color of the text.
            alpha (int): The alpha value for transparency (0-255).
            
        Returns:
            Surface: A surface containing the rendered text with the specified alpha.
        """
        # Render text
        text_surface = font.render(text, True, color)
        
        # Create surface with alpha
        alpha_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        alpha_surface.fill((0, 0, 0, 0))  # Transparent
        alpha_surface.blit(text_surface, (0, 0))
        
        # Apply alpha
        alpha_surface.set_alpha(alpha)
        
        return alpha_surface
    
    def clear_cache(self):
        """Clear the cached surfaces to free memory."""
        self._cached_surfaces.clear()