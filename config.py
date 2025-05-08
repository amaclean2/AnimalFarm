"""
Configuration settings for the Agent Survival Simulation.

This module centralizes all configurable parameters for the simulation,
making it easy to adjust various aspects of the simulation behavior
without modifying the core code.
"""

#------------------------------------------------------------------------------
# Display Settings
#------------------------------------------------------------------------------

# Basic display settings
CELL_SIZE = 22                       # Size of each cell in pixels (increased from 20)
WORLD_SIZE = 50                      # Size of the world grid (WORLD_SIZE x WORLD_SIZE)

# Viewport settings
VIEWPORT_WIDTH = 35                  # How many cells wide the viewport is (increased from 30)
VIEWPORT_HEIGHT = 28                 # How many cells tall the viewport is (increased from 25)
STATUS_PANEL_HEIGHT = 140            # Height of the status panel in pixels

# Screen dimensions (calculated from the above)
SCREEN_WIDTH = VIEWPORT_WIDTH * CELL_SIZE
SCREEN_HEIGHT = VIEWPORT_HEIGHT * CELL_SIZE + STATUS_PANEL_HEIGHT

# Rendering settings
FPS = 5                              # Frames per second cap

#------------------------------------------------------------------------------
# Color Definitions
#------------------------------------------------------------------------------

# Basic colors
COLOR = {
    # UI Colors
    'WHITE': (255, 255, 255),        # Background (day)
    'BLACK': (0, 0, 0),              # Text and outlines
    'GRAY': (200, 200, 200),         # Panel backgrounds
    'RED': (255, 0, 0),              # Warnings and alerts
    'YELLOW': (255, 255, 0),         # Highlights and indicators
    
    # World Colors
    'GREEN': (0, 200, 0),            # Cells with resources (day)
    'BROWN': (139, 69, 19),          # Consumed cells (day)
    'LIGHT_GREEN': (144, 238, 144),  # Regrowing cells (day)
    
    # Night Colors
    'DARK_BLUE': (0, 0, 100),        # Background (night)
    'DARK_GREEN': (0, 100, 0),       # Cells with resources (night)
    'DARK_BROWN': (80, 40, 10),      # Consumed cells (night)
    'DARK_LIGHT_GREEN': (80, 120, 80),  # Regrowing cells (night)
    
    # Special Effects
    'BLUE': (0, 0, 255),             # Sleep energy
    'TRANSPARENT_YELLOW': (255, 255, 0, 30)  # Sensing range visualization
}

#------------------------------------------------------------------------------
# World Settings
#------------------------------------------------------------------------------

# Resource settings
INITIAL_RESOURCE_PERCENTAGE = 0.1    # Percentage of cells that start with resources
RESOURCE_VALUE = 2                   # Caloric value of each cell's resources

# Regrowth settings
REGROWTH_ENABLED = True              # Whether cells can regrow resources
MIN_REGROWTH_TIME = 100              # Minimum turns for a cell to regenerate
MAX_REGROWTH_TIME = 200              # Maximum turns for a cell to regenerate

#------------------------------------------------------------------------------
# Time System Settings
#------------------------------------------------------------------------------

# Day/night cycle
MOVES_PER_DAY = 10                   # Number of moves the agent makes per day

#------------------------------------------------------------------------------
# Agent Settings
#------------------------------------------------------------------------------

# Energy settings
INITIAL_CALORIES = 20                # Starting calories
MAX_CALORIES = 50                    # Maximum calorie storage
INITIAL_SLEEP = 100                  # Starting sleep energy
MAX_SLEEP = 100                      # Maximum sleep energy
SLEEP_ENERGY_GAIN = 10               # Sleep energy gained per turn while sleeping
CALORIE_CONSUMPTION_PER_DAY = 15     # Calories consumed each night

# Movement settings
RESOURCE_SENSING_RANGE = 4           # How far the agent can "see" resources
OPTIMAL_CHOICE_PROBABILITY = 0.8     # Probability of choosing the closest resource
SENSING_VISUALIZATION_RADIUS = RESOURCE_SENSING_RANGE * CELL_SIZE

#------------------------------------------------------------------------------
# Multi-Agent Settings
#------------------------------------------------------------------------------

# Agent colors (used for identification)
AGENT_COLORS = {
    'agent1': {
        'awake': COLOR['RED'],
        'asleep': COLOR['BLUE']
    },
    'agent2': {
        'awake': (255, 165, 0),      # Orange
        'asleep': (0, 128, 128)      # Teal
    },
    'agent3': {
        'awake': (0, 200, 100),      # Green
        'asleep': (100, 0, 200)      # Purple
    },
    'agent4': {
        'awake': (255, 215, 0),      # Gold
        'asleep': (0, 0, 128)        # Navy
    }
}

# Starting positions (as fractions of world size)
AGENT_START_POSITIONS = [
    (0.25, 0.25),                    # Northwest
    (0.75, 0.25),                    # Northeast
    (0.25, 0.75),                    # Southwest
    (0.75, 0.75)                     # Southeast
]

#------------------------------------------------------------------------------
# Debug Settings
#------------------------------------------------------------------------------

# Debug options
DEBUG_MODE = False                   # Enable/disable debug features
SHOW_SENSING_RANGE = True            # Show the agent's sensing range
CAMERA_SMOOTHING = 0.2               # Camera movement smoothing (0.0 to 1.0)