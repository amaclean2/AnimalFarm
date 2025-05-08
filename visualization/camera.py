"""
Camera system for the Agent Survival Simulation.

The Camera class provides a viewport into the larger world, allowing the
simulation to display only a portion of the world centered on a point of
interest, typically the active agent.
"""
from config import VIEWPORT_WIDTH, VIEWPORT_HEIGHT, WORLD_SIZE

class Camera:
    """
    A camera that follows a target and provides a viewport into the world.
    
    The camera defines a rectangular region of the world that is currently
    visible on screen. It can be moved to follow a target (like an agent)
    and provides coordinate conversion between world and screen space.
    """
    
    def __init__(self):
        """
        Initialize the camera.
        
        The camera starts centered on the middle of the world.
        """
        # Position (top-left corner in world coordinates)
        self.x = 0
        self.y = 0
        
        # Viewport dimensions (in world cells)
        self.width = VIEWPORT_WIDTH
        self.height = VIEWPORT_HEIGHT
        
        # Smoothing settings for camera movement
        self.smoothing = 0.2  # Lower = smoother (0 to 1)
        self._target_x = 0
        self._target_y = 0
    
    def update(self, target_x, target_y):
        """
        Update the camera position to center on a target.
        
        Args:
            target_x (int): The target x position in world coordinates.
            target_y (int): The target y position in world coordinates.
        """
        # Store the target position
        self._target_x = target_x
        self._target_y = target_y
        
        # Calculate the desired center position
        desired_x = target_x - self.width // 2
        desired_y = target_y - self.height // 2
        
        # Apply smoothing if enabled
        if self.smoothing > 0:
            self._apply_smoothing(desired_x, desired_y)
        else:
            self.x = desired_x
            self.y = desired_y
        
        # Ensure camera doesn't go out of world bounds
        self._clamp_to_world_bounds()
    
    def _apply_smoothing(self, desired_x, desired_y):
        """
        Apply smoothing to camera movement.
        
        Args:
            desired_x (int): The desired x position.
            desired_y (int): The desired y position.
        """
        # Interpolate between current and desired position
        self.x += int((desired_x - self.x) * self.smoothing)
        self.y += int((desired_y - self.y) * self.smoothing)
    
    def _clamp_to_world_bounds(self):
        """Ensure the camera remains within the world boundaries."""
        self.x = max(0, min(self.x, WORLD_SIZE - self.width))
        self.y = max(0, min(self.y, WORLD_SIZE - self.height))
    
    def world_to_screen(self, world_x, world_y):
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            world_x (int): The x position in world coordinates.
            world_y (int): The y position in world coordinates.
            
        Returns:
            tuple: (screen_x, screen_y) position on screen, or None if outside viewport.
        """
        # Calculate screen position (relative to viewport)
        screen_x = world_x - self.x
        screen_y = world_y - self.y
        
        # Check if the position is within the viewport
        if self.is_visible(world_x, world_y):
            return screen_x, screen_y
        return None
    
    def screen_to_world(self, screen_x, screen_y):
        """
        Convert screen coordinates to world coordinates.
        
        Args:
            screen_x (int): The x position in screen coordinates.
            screen_y (int): The y position in screen coordinates.
            
        Returns:
            tuple: (world_x, world_y) position in the world.
        """
        world_x = screen_x + self.x
        world_y = screen_y + self.y
        return world_x, world_y
    
    def is_visible(self, world_x, world_y):
        """
        Check if a world position is visible in the current viewport.
        
        Args:
            world_x (int): The x position in world coordinates.
            world_y (int): The y position in world coordinates.
            
        Returns:
            bool: True if the position is visible, False otherwise.
        """
        return (self.x <= world_x < self.x + self.width and 
                self.y <= world_y < self.y + self.height)
    
    def get_visible_rect(self):
        """
        Get the rectangle of world coordinates currently visible.
        
        Returns:
            tuple: (left, top, width, height) of the visible area in world coordinates.
        """
        return (self.x, self.y, self.width, self.height)
    
    def set_position(self, x, y):
        """
        Set the camera position directly.
        
        Args:
            x (int): The x position in world coordinates.
            y (int): The y position in world coordinates.
        """
        self.x = x
        self.y = y
        self._clamp_to_world_bounds()
    
    def center_on(self, world_x, world_y, immediate=True):
        """
        Center the camera on a specific world position.
        
        Args:
            world_x (int): The x position in world coordinates.
            world_y (int): The y position in world coordinates.
            immediate (bool): If True, move immediately; if False, use smoothing.
        """
        self._target_x = world_x
        self._target_y = world_y
        
        # Calculate the center position
        center_x = world_x - self.width // 2
        center_y = world_y - self.height // 2
        
        if immediate:
            self.x = center_x
            self.y = center_y
            self._clamp_to_world_bounds()
        else:
            # Use update which applies smoothing
            self.update(world_x, world_y)
    
    def get_target_position(self):
        """
        Get the current target position.
        
        Returns:
            tuple: (target_x, target_y) in world coordinates.
        """
        return (self._target_x, self._target_y)
    
    def get_center_position(self):
        """
        Get the world coordinates at the center of the viewport.
        
        Returns:
            tuple: (center_x, center_y) in world coordinates.
        """
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2
        return (center_x, center_y)
    
    def set_smoothing(self, smoothing):
        """
        Set the camera movement smoothing factor.
        
        Args:
            smoothing (float): A value from 0 to 1, where 0 is no smoothing
                               and 1 is maximum smoothing.
        """
        self.smoothing = max(0, min(1, smoothing))