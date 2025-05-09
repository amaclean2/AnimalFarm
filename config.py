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
CELL_SIZE = 25                       # Size of each cell in pixels
WORLD_SIZE = 50                      # Size of the world grid (WORLD_SIZE x WORLD_SIZE)

# Viewport settings
VIEWPORT_WIDTH = 40                  # How many cells wide the viewport is
VIEWPORT_HEIGHT = 30                 # How many cells tall the viewport is
STATUS_PANEL_HEIGHT = 230            # Height of the status panel in pixels

# Screen dimensions (calculated from the above)
SCREEN_WIDTH = VIEWPORT_WIDTH * CELL_SIZE
SCREEN_HEIGHT = VIEWPORT_HEIGHT * CELL_SIZE + STATUS_PANEL_HEIGHT

# Rendering settings
FPS = 12                             # Frames per second cap

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
# Resource Types and Values
#------------------------------------------------------------------------------

# Define resource types and their properties
RESOURCE_TYPES = ["food", "water"]  # All resource types in the simulation

# Resource values (how much benefit agent gets from each type)
RESOURCE_VALUE = {
    "default": 10,       # Default resource value
    "food": 20,          # Food provides calories
    "water": 15          # Water provides hydration
}

# Resource colors for visualization
RESOURCE_COLORS = {
    "food": (0, 200, 0),      # Green for food
    "water": (0, 100, 255)    # Blue for water
}

#------------------------------------------------------------------------------
# Resource Cluster Settings
#------------------------------------------------------------------------------

# Food cluster settings
FOOD_CLUSTER_COUNT = 6               # Number of food clusters in the world
FOOD_CLUSTER_SIZE_RANGE = (10, 30)   # Min/max number of cells per food cluster
FOOD_CLUSTER_DENSITY = 0.7           # Probability of spreading to adjacent cells

# Water cluster settings
WATER_CLUSTER_COUNT = 3              # Number of water sources
WATER_CLUSTER_SIZE_RANGE = (20, 40)  # Min/max size for water clusters
WATER_CLUSTER_DENSITY = 0.8          # Probability of spreading to adjacent cells

# Overall resource distribution
INITIAL_RESOURCE_PERCENTAGE = 0.03    # Approximate percentage of cells with resources

#------------------------------------------------------------------------------
# World Settings
#------------------------------------------------------------------------------

# Regrowth settings
REGROWTH_ENABLED = True              # Whether cells can regrow resources
MIN_REGROWTH_TIME = 300              # Minimum turns for a cell to regenerate
MAX_REGROWTH_TIME = 400              # Maximum turns for a cell to regenerate

#------------------------------------------------------------------------------
# Time System Settings
#------------------------------------------------------------------------------

# Day/night cycle
MOVES_PER_DAY = 20                   # Number of moves the agent makes per day

#------------------------------------------------------------------------------
# Agent Settings
#------------------------------------------------------------------------------

# Energy settings
INITIAL_CALORIES = 20                # Starting calories
MAX_CALORIES = 50                    # Maximum calorie storage
INITIAL_SLEEP = 100                  # Starting sleep energy
MAX_SLEEP = 100                      # Maximum sleep energy
SLEEP_ENERGY_GAIN = 10               # Sleep energy gained per turn while sleeping
CALORIE_CONSUMPTION_PER_DAY = 25     # Calories consumed each night

# Water settings
INITIAL_WATER = 30                   # Starting water level
MAX_WATER = 70                       # Maximum water storage
WATER_CONSUMPTION_PER_DAY = 20       # Water consumed each night

# Movement settings
RESOURCE_SENSING_RANGE = 4           # How far the agent can "see" resources
OPTIMAL_CHOICE_PROBABILITY = 0.8     # Probability of choosing the closest resource
SENSING_VISUALIZATION_RADIUS = RESOURCE_SENSING_RANGE * CELL_SIZE

#------------------------------------------------------------------------------
# Home Base Settings
#------------------------------------------------------------------------------

# Home base configuration
HOME_BASE_POSITION = (25, 25)        # (x, y) coordinates of the home base (center of the world)
HOME_BASE_ENABLED = True             # Whether agents return to home base at night

#------------------------------------------------------------------------------
# Multi-Agent Settings
#------------------------------------------------------------------------------

# Number of agents in the simulation
NUM_AGENTS = 4                      # Number of agents in the simulation

# Agent roles
AGENT_ROLES = {
    "food_gatherer": {
        "description": "Specializes in gathering food resources",
        "sensing_boost": 1.5,       # Better at finding food
    },
    "water_gatherer": {
        "description": "Specializes in gathering water resources",
        "sensing_boost": 1.5,       # Better at finding water
    },
    "explorer": {
        "description": "Specializes in exploring new territory",
        "move_boost": 1.5,          # Can move faster/more efficiently
    },
    "generalist": {
        "description": "Balanced abilities across all tasks",
        "efficiency_boost": 1.2,    # Slightly more efficient at everything
    }
}

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
# Note: These are ignored if HOME_BASE_ENABLED is True, as all agents will start at the home base
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