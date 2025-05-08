"""
Game UI elements for the Agent Survival Simulation.

This module provides UI components for game-level displays such as the
game over screen, pause menu, and other full-screen overlays.
"""
import pygame
import math
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
        self.title_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.subtitle_font = pygame.font.SysFont('Arial', 32, bold=True)
        self.medium_font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        
        # Create overlay surface
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    def draw_game_over(self, screen, agent):
        """
        Display game over message and statistics.
        
        Args:
            screen: The pygame screen to draw on.
            agent (Agent): The agent that survived the longest.
        """
        # Draw overlay
        self.overlay.fill((0, 0, 0, 180))
        screen.blit(self.overlay, (0, 0))
        
        # Game over title
        title_surface = self.title_font.render("GAME OVER", True, COLOR['RED'])
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 80))
        screen.blit(title_surface, title_rect)
        
        # Winner text
        winner_surface = self.medium_font.render(
            f"{agent.agent_id} survived the longest", True, COLOR['WHITE']
        )
        winner_rect = winner_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
        screen.blit(winner_surface, winner_rect)
        
        # Days survived
        days_surface = self.medium_font.render(
            f"Days survived: {agent.days_survived}", True, COLOR['WHITE']
        )
        days_rect = days_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(days_surface, days_rect)
        
        # Death reason
        death_reason = "Starvation" if agent.calories <= 0 else "Exhaustion"
        death_surface = self.medium_font.render(
            f"Cause of death: {death_reason}", True, COLOR['WHITE']
        )
        death_rect = death_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30))
        screen.blit(death_surface, death_rect)
        
        restart_surface = self.medium_font.render("Press 'R' to restart", True, COLOR['WHITE'])
        restart_rect = restart_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 70))
        screen.blit(restart_surface, restart_rect)
    
    def draw_pause_menu(self, screen):
        """
        Display the pause menu.
        
        Args:
            screen: The pygame screen to draw on.
        """
        # Draw overlay
        self.overlay.fill((0, 0, 0, 120))
        screen.blit(self.overlay, (0, 0))
        
        # Pause title
        pause_surface = self.title_font.render("PAUSED", True, COLOR['WHITE'])
        text_rect = pause_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        screen.blit(pause_surface, text_rect)
        
        # Instructions
        instructions = [
            "Press SPACE to resume",
            "Press R to restart",
            "Press ESC to quit"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_surface = self.medium_font.render(instruction, True, COLOR['WHITE'])
            inst_rect = inst_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + i * 30))
            screen.blit(inst_surface, inst_rect)