"""
Entry point for the Agent Survival Simulation.

This module serves as the main entry point for the simulation, handling
initialization, command-line arguments, and launching the game. It sets up
the pygame environment and creates the main game instance.
"""
import sys
import argparse
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DEBUG_MODE, FPS
from simulation.game import Game

def parse_arguments():
    """
    Parse command-line arguments for the simulation.
    
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Agent Survival Simulation')
    
    # Simulation configuration options
    parser.add_argument('--fps', type=int, default=FPS,
                      help=f'Frames per second (default: {FPS})')
    parser.add_argument('--debug', action='store_true', default=DEBUG_MODE,
                      help='Enable debug mode')
    parser.add_argument('--agents', type=int, default=4,
                      help='Number of agents (1-4, default: 4)')
    
    # Display options
    parser.add_argument('--fullscreen', action='store_true',
                      help='Run in fullscreen mode')
    parser.add_argument('--width', type=int, default=SCREEN_WIDTH,
                      help=f'Screen width in pixels (default: {SCREEN_WIDTH})')
    parser.add_argument('--height', type=int, default=SCREEN_HEIGHT,
                      help=f'Screen height in pixels (default: {SCREEN_HEIGHT})')
    
    return parser.parse_args()

def setup_pygame(args):
    """
    Initialize pygame and create the game window.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        pygame.Surface: The main screen surface.
    """
    # Initialize pygame
    pygame.init()
    
    # Set up the display
    if args.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        print(f"Running in fullscreen mode: {screen.get_width()}x{screen.get_height()}")
    else:
        screen = pygame.display.set_mode((args.width, args.height))
        print(f"Window size: {args.width}x{args.height}")
    
    # Set window title and icon
    pygame.display.set_caption("Multi-Agent Survival Simulation")
    
    # Set up the clock to control frame rate
    pygame.time.Clock().tick(args.fps)
    
    return screen

def main():
    """
    Main entry point for the simulation.
    
    This function initializes pygame, creates the game window, and starts
    the main game loop. It also handles clean-up when the game exits.
    
    Returns:
        int: Exit code (0 for normal exit, non-zero for error).
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    try:
        # Set up pygame and create the window
        screen = setup_pygame(args)
        
        # Print startup information
        print(f"Starting Multi-Agent Survival Simulation with {args.agents} agents")
        print(f"FPS: {args.fps}, Debug mode: {'Enabled' if args.debug else 'Disabled'}")
        
        # Create and configure the game
        game = Game(screen)
        game.set_agent_count(args.agents)
        game.set_debug_mode(args.debug)
        game.set_fps(args.fps)
        
        # Run the game
        exit_code = game.run()
        
        # Clean up pygame
        pygame.quit()
        
        # Print exit message
        print(f"Simulation ended with exit code: {exit_code}")
        
        return exit_code
        
    except Exception as e:
        # Handle any unexpected errors
        print(f"Error: {e}")
        pygame.quit()
        return 1
    
if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nSimulation terminated by user")
        pygame.quit()
        sys.exit(0)