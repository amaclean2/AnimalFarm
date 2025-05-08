"""
World class for the Agent Survival Simulation.

The World class represents the environment in which agents operate.
It contains a grid of cells, manages resource distribution, and handles
the visualization of the environment.
"""
import random
from models.cell import Cell
from config import WORLD_SIZE, INITIAL_RESOURCE_PERCENTAGE

class World:
    """
    Represents the 2D grid world in which agents operate.
    
    The world is a grid of cells, some with resources and some depleted.
    It manages the distribution of resources, cell updates, and provides
    methods for agents to interact with cells.
    """
    
    def __init__(self, width=WORLD_SIZE, height=WORLD_SIZE):
        """
        Initialize the world with a random distribution of resources.
        
        Args:
            width (int): The width of the world in cells.
            height (int): The height of the world in cells.
        """
        self.width = width
        self.height = height
        self.grid = self._create_grid()
        self.statistics = {
            'total_cells': width * height,
            'initialized_with_resources': int(width * height * INITIAL_RESOURCE_PERCENTAGE)
        }
    
    def _create_grid(self):
        """
        Create a 2D grid of cells with random resource distribution.
        
        Returns:
            list: 2D list of Cell objects.
        """
        # Create a grid of cells, initially without resources
        grid = [[Cell(has_resources=False) for _ in range(self.height)] for _ in range(self.width)]
        
        # Determine which cells will have resources
        resource_coords = self._determine_resource_positions()
        
        # Set resources for the selected cells
        for x, y in resource_coords:
            grid[x][y] = Cell(has_resources=True)
        
        return grid
    
    def _determine_resource_positions(self):
        """
        Determine which positions in the grid will have resources.
        
        Returns:
            list: List of (x, y) coordinates that will have resources.
        """
        # Calculate number of cells that should have resources
        total_cells = self.width * self.height
        cells_with_resources = int(total_cells * INITIAL_RESOURCE_PERCENTAGE)
        
        # Get all coordinates
        all_coords = [(x, y) for x in range(self.width) for y in range(self.height)]
        
        # Randomly select which cells will have resources
        return random.sample(all_coords, cells_with_resources)
    
    def update(self):
        """
        Update all cells in the world for one turn.
        
        This method progresses all time-dependent processes like cell regrowth.
        """
        for x in range(self.width):
            for y in range(self.height):
                self.grid[x][y].update()
    
    def get_cell(self, x, y):
        """
        Get the cell at the specified coordinates.
        
        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            Cell: The cell at the specified coordinates, or None if invalid.
        """
        if self.is_valid_position(x, y):
            return self.grid[x][y]
        return None
    
    def is_valid_position(self, x, y):
        """
        Check if the given position is valid (within world bounds).
        
        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.
            
        Returns:
            bool: True if the position is valid, False otherwise.
        """
        return 0 <= x < self.width and 0 <= y < self.height
    
    def has_resources(self, x, y):
        """
        Check if the cell at the given position has resources.
        
        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.
            
        Returns:
            bool: True if the cell has resources, False otherwise.
        """
        cell = self.get_cell(x, y)
        return cell is not None and cell.state == Cell.STATE_FULL
    
    def consume_resources(self, x, y):
        """
        Consume resources at the given position.
        
        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            int: The amount of calories obtained, or 0 if none.
        """
        cell = self.get_cell(x, y)
        if cell:
            return cell.consume()
        return 0
    
    def count_cells_by_state(self):
        """
        Count cells in each state (full, consumed, regrowing).
        
        Returns:
            dict: A dictionary with counts for each cell state.
        """
        counts = {
            'full': 0,
            'consumed': 0,
            'regrowing': 0,
            'total': self.width * self.height
        }
        
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell.state == Cell.STATE_FULL:
                    counts['full'] += 1
                elif cell.state == Cell.STATE_CONSUMED:
                    counts['consumed'] += 1
                elif cell.state == Cell.STATE_REGROWING:
                    counts['regrowing'] += 1
        
        # Calculate percentages
        for key in ['full', 'consumed', 'regrowing']:
            counts[f'{key}_percent'] = (counts[key] / counts['total']) * 100
            
        return counts
    
    def count_consumed_cells(self):
        """
        Count how many cells have been consumed in the world.
        
        Returns:
            int: The number of consumed or regrowing cells.
            float: The percentage of consumed or regrowing cells.
        """
        consumed = sum(sum(1 for cell in row if cell.state != Cell.STATE_FULL) for row in self.grid)
        total = self.width * self.height
        percentage = (consumed / total) * 100
        return consumed, percentage
    
    def get_resource_density_heat_map(self):
        """
        Generate a heat map of resource density in the world.
        
        Returns:
            list: 2D list with values from 0 to 1 representing resource density.
        """
        heat_map = [[0 for _ in range(self.height)] for _ in range(self.width)]
        
        # Compute local resource density for each cell
        for x in range(self.width):
            for y in range(self.height):
                heat_map[x][y] = self._calculate_local_resource_density(x, y)
                
        return heat_map
    
    def _calculate_local_resource_density(self, x, y, radius=3):
        """
        Calculate the resource density in the local area around a cell.
        
        Args:
            x (int): The x-coordinate of the center cell.
            y (int): The y-coordinate of the center cell.
            radius (int): The radius to consider around the cell.
            
        Returns:
            float: A value from 0 to 1 representing local resource density.
        """
        total_cells = 0
        resource_cells = 0
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if self.is_valid_position(nx, ny):
                    total_cells += 1
                    if self.grid[nx][ny].state == Cell.STATE_FULL:
                        resource_cells += 1
        
        return resource_cells / max(1, total_cells)
    
    def draw(self, screen, night_mode=False, camera=None):
        """
        Draw the entire world grid on the screen.
        
        Args:
            screen: The pygame screen to draw on.
            night_mode (bool): Whether to use night colors.
            camera (Camera): Camera used for viewport rendering.
        """
        # If no camera is provided, draw the entire world (not recommended for large worlds)
        if camera is None:
            self._draw_entire_world(screen, night_mode)
            return
            
        # Draw only the visible portion of the world through the camera
        self._draw_visible_portion(screen, night_mode, camera)
    
    def _draw_entire_world(self, screen, night_mode):
        """Draw the entire world (use with caution for large worlds)."""
        for y in range(self.height):
            for x in range(self.width):
                self.grid[x][y].draw(screen, x, y, night_mode)
    
    def _draw_visible_portion(self, screen, night_mode, camera):
        """Draw only the portion of the world visible through the camera."""
        # Calculate the visible range
        start_x = max(0, camera.x)
        end_x = min(camera.x + camera.width, self.width)
        start_y = max(0, camera.y)
        end_y = min(camera.y + camera.height, self.height)
        
        # Draw only cells in the visible range
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Convert world coordinates to screen coordinates
                screen_pos = camera.world_to_screen(x, y)
                if screen_pos:
                    self.grid[x][y].draw(screen, screen_pos[0], screen_pos[1], night_mode)