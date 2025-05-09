"""
Cell class for the Agent Survival Simulation.

The Cell class represents a single location in the world grid that may contain
resources which agents can collect. Cells have different states (full, consumed,
or regrowing) and can visually represent their state.
"""
import pygame
import random
from config import (
    CELL_SIZE, COLOR, RESOURCE_VALUE, 
    MIN_REGROWTH_TIME, MAX_REGROWTH_TIME, REGROWTH_ENABLED,
    RESOURCE_TYPES, RESOURCE_COLORS
)

class Cell:
    """
    Represents a single cell in the world grid.
    
    Each cell can contain resources that agents can consume. After consumption,
    cells may regrow their resources over time if regrowth is enabled.
    """
    
    # Cell state constants
    STATE_FULL = 0       # Cell has resources
    STATE_CONSUMED = 1   # Cell is consumed and has no resources
    STATE_REGROWING = 2  # Cell is in the process of regrowing
    
    def __init__(self, has_resources=True, resource_type=None):
        """
        Initialize a new cell.
        
        Args:
            has_resources (bool): Whether this cell starts with resources.
            resource_type (str): Type of resource in this cell ("food", "water", etc.)
        """
        self.resource_type = resource_type
        self._initialize_resources(has_resources)
        self._initialize_regrowth()
        
        # Cluster tracking
        self.cluster_id = None
    
    def _initialize_resources(self, has_resources):
        """Initialize the cell's resource state."""
        # Use resource type-specific value if available
        if has_resources and self.resource_type and self.resource_type in RESOURCE_VALUE:
            self.resources = RESOURCE_VALUE[self.resource_type]
        elif has_resources:
            self.resources = RESOURCE_VALUE["default"]
        else:
            self.resources = 0
            
        self.state = self.STATE_FULL if has_resources else self.STATE_CONSUMED
    
    def _initialize_regrowth(self):
        """Initialize the cell's regrowth properties."""
        # Assign a random regrowth time within the configured range
        self.regrowth_time = random.randint(MIN_REGROWTH_TIME, MAX_REGROWTH_TIME)
        self.regrowth_counter = 0
    
    def has_resources(self):
        """
        Check if this cell has resources available.
        
        Returns:
            bool: True if the cell has resources, False otherwise.
        """
        return self.state == self.STATE_FULL
    
    def consume(self):
        """
        Consume the resources from this cell and return the caloric value.
        
        When a cell is consumed, it transitions to either CONSUMED or REGROWING state
        depending on whether regrowth is enabled.
        
        Returns:
            tuple: (value, resource_type) - The amount of value obtained and the type of resource.
        """
        if self.state == self.STATE_FULL:
            return self._perform_consumption()
        return 0, None
    
    def _perform_consumption(self):
        """
        Handle the actual consumption of resources.
        
        Returns:
            tuple: (value, resource_type) - The amount of value obtained and the type of resource.
        """
        resources_gained = self.resources
        resource_type = self.resource_type
        self.resources = 0
        
        # Start regrowth process if enabled, otherwise mark as consumed
        if REGROWTH_ENABLED:
            self.state = self.STATE_REGROWING
            self.regrowth_counter = 0
        else:
            self.state = self.STATE_CONSUMED
            
        return resources_gained, resource_type
    
    def update(self):
        """
        Update the cell state, handling regrowth if applicable.
        
        This method should be called once per simulation turn to progress
        the regrowth of consumed cells.
        """
        if not REGROWTH_ENABLED:
            return
            
        if self.state == self.STATE_REGROWING:
            self._progress_regrowth()
    
    def _progress_regrowth(self):
        """Progress the regrowth of this cell."""
        self.regrowth_counter += 1
        if self.regrowth_counter >= self.regrowth_time:
            self._complete_regrowth()
    
    def _complete_regrowth(self):
        """Complete the regrowth process, restoring resources."""
        self.state = self.STATE_FULL
        
        # Use resource type-specific value if available
        if self.resource_type and self.resource_type in RESOURCE_VALUE:
            self.resources = RESOURCE_VALUE[self.resource_type]
        else:
            self.resources = RESOURCE_VALUE["default"]
            
        self.regrowth_counter = 0
        
        # Assign a new random regrowth time for next cycle
        self.regrowth_time = random.randint(MIN_REGROWTH_TIME, MAX_REGROWTH_TIME)
    
    def get_regrowth_percentage(self):
        """
        Calculate what percentage of regrowth is complete.
        
        Returns:
            float: Percentage from 0.0 to 1.0, or 0 if not regrowing.
        """
        if self.state != self.STATE_REGROWING or self.regrowth_time == 0:
            return 0.0
        return min(1.0, self.regrowth_counter / self.regrowth_time)
    
    def draw(self, screen, x, y, night_mode=False):
        """
        Draw the cell on the screen.
        
        Args:
            screen: The pygame screen to draw on.
            x (int): The x-coordinate on the screen.
            y (int): The y-coordinate on the screen.
            night_mode (bool): Whether to use night colors.
        """
        # Create the cell rectangle
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        
        # Get the appropriate color for the cell's state
        color = self._get_cell_color(night_mode)
            
        # Draw the cell
        pygame.draw.rect(screen, color, rect)
        
        # Draw regrowth indicator if applicable
        if self.state == self.STATE_REGROWING:
            self._draw_regrowth_indicator(screen, rect)
    
    def _get_cell_color(self, night_mode):
        """Get the appropriate color based on cell state, resource type, and time of day."""
        # Default colors
        if night_mode:
            full_color = COLOR['DARK_GREEN']  # Default full cell color (night)
            regrowing_color = COLOR['DARK_LIGHT_GREEN']  # Default regrowing color (night)
            consumed_color = COLOR['DARK_BROWN']  # Default consumed color (night)
        else:
            full_color = COLOR['GREEN']  # Default full cell color (day)
            regrowing_color = COLOR['LIGHT_GREEN']  # Default regrowing color (day)
            consumed_color = COLOR['BROWN']  # Default consumed color (day)
        
        # Use resource-specific colors if available
        if self.resource_type and self.resource_type in RESOURCE_COLORS:
            if night_mode:
                # Darken the color for night mode
                day_color = RESOURCE_COLORS[self.resource_type]
                full_color = (day_color[0]//2, day_color[1]//2, day_color[2]//2)
                regrowing_color = (day_color[0]//3, day_color[1]//3, day_color[2]//3)
            else:
                full_color = RESOURCE_COLORS[self.resource_type]
                # Create a lighter version for regrowing
                regrowing_color = (
                    min(255, full_color[0] + 80),
                    min(255, full_color[1] + 80),
                    min(255, full_color[2] + 80)
                )
        
        # Return the appropriate color based on cell state
        if self.state == self.STATE_FULL:
            return full_color
        elif self.state == self.STATE_REGROWING:
            return regrowing_color
        else:  # STATE_CONSUMED
            return consumed_color
    
    def _draw_regrowth_indicator(self, screen, rect):
        """Draw an indicator showing regrowth progress."""
        # Only draw if in the regrowing state
        if self.state != self.STATE_REGROWING:
            return
            
        # Calculate regrowth percentage
        regrowth_pct = self.get_regrowth_percentage()
        
        # Draw a small indicator at the bottom of the cell
        indicator_height = max(1, int(CELL_SIZE * 0.2))
        indicator_width = int(CELL_SIZE * regrowth_pct)
        
        indicator_rect = pygame.Rect(
            rect.left,
            rect.bottom - indicator_height,
            indicator_width,
            indicator_height
        )
        
        # Use resource-specific colors for the indicator if available
        if self.resource_type and self.resource_type in RESOURCE_COLORS:
            indicator_color = RESOURCE_COLORS[self.resource_type]
        else:
            indicator_color = COLOR['GREEN']
            
        pygame.draw.rect(screen, indicator_color, indicator_rect)