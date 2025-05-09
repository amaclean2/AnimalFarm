"""
World class for the Agent Survival Simulation.

The World class represents the environment in which agents operate.
It contains a grid of cells, manages resource distribution, and handles
the visualization of the environment.
"""
import random
import math
from models.cell import Cell
from config import (
    WORLD_SIZE, INITIAL_RESOURCE_PERCENTAGE, 
    FOOD_CLUSTER_COUNT, FOOD_CLUSTER_SIZE_RANGE, FOOD_CLUSTER_DENSITY,
    WATER_CLUSTER_COUNT, WATER_CLUSTER_SIZE_RANGE, WATER_CLUSTER_DENSITY,
    RESOURCE_TYPES
)

class World:
    """
    Represents the 2D grid world in which agents operate.
    
    The world is a grid of cells, some with resources and some depleted.
    It manages the distribution of resources, cell updates, and provides
    methods for agents to interact with cells.
    """
    
    def __init__(self, width=WORLD_SIZE, height=WORLD_SIZE):
        """
        Initialize the world with clustered resource distribution.
        
        Args:
            width (int): The width of the world in cells.
            height (int): The height of the world in cells.
        """
        self.width = width
        self.height = height
        self.grid = self._create_empty_grid()
        self.clusters = []  # Store information about resource clusters
        
        # Generate resource clusters
        self._generate_resource_clusters()
        
        # Track statistics
        self._update_statistics()
    
    def _create_empty_grid(self):
        """
        Create a 2D grid of empty cells.
        
        Returns:
            list: 2D list of Cell objects with no resources.
        """
        return [[Cell(has_resources=False, resource_type=None) for _ in range(self.height)] 
                for _ in range(self.width)]
    
    def _generate_resource_clusters(self):
        """
        Generate clusters of resources throughout the world.
        Uses a seed-and-grow algorithm to create natural-looking clusters.
        """
        cluster_id = 0
        
        # Generate food clusters
        self._generate_clusters("food", FOOD_CLUSTER_COUNT, FOOD_CLUSTER_SIZE_RANGE, 
                               FOOD_CLUSTER_DENSITY, cluster_id)
        cluster_id += FOOD_CLUSTER_COUNT
        
        # Generate water clusters
        self._generate_clusters("water", WATER_CLUSTER_COUNT, WATER_CLUSTER_SIZE_RANGE, 
                               WATER_CLUSTER_DENSITY, cluster_id)
    
    def _generate_clusters(self, resource_type, count, size_range, density, start_id):
        """
        Generate clusters of a specific resource type.
        
        Args:
            resource_type: Type of resource to generate ("food", "water", etc.)
            count: Number of clusters to generate
            size_range: (min_size, max_size) tuple for cluster sizes
            density: Probability of spreading to adjacent cells
            start_id: Starting cluster ID
        """
        for i in range(count):
            cluster_id = start_id + i
            
            # Choose a random center point for the cluster
            center_x = random.randint(0, self.width - 1)
            center_y = random.randint(0, self.height - 1)
            
            # Determine cluster size
            min_size, max_size = size_range
            target_size = random.randint(min_size, max_size)
            
            # Track cells in this cluster
            cluster_cells = []
            
            # Create the cluster using the seed and grow method
            self._grow_cluster(center_x, center_y, target_size, resource_type, 
                             cluster_id, cluster_cells, density)
            
            # Store cluster information
            self.clusters.append({
                'id': cluster_id,
                'type': resource_type,
                'center': (center_x, center_y),
                'size': len(cluster_cells),
                'cells': cluster_cells
            })
            
            print(f"Generated {resource_type} cluster #{cluster_id} with {len(cluster_cells)} cells")
    
    def _grow_cluster(self, center_x, center_y, target_size, resource_type, 
                     cluster_id, cluster_cells, density):
        """
        Grow a cluster from a center point using a probability-based spreading algorithm.
        
        Args:
            center_x, center_y: Center coordinates for the cluster
            target_size: Desired number of cells in the cluster
            resource_type: Type of resource for this cluster ("food", "water", etc.)
            cluster_id: Unique identifier for this cluster
            cluster_cells: List to store the coordinates of cells in this cluster
            density: Probability of spreading to adjacent cells
        """
        # Initial cell of the cluster
        self.grid[center_x][center_y] = Cell(has_resources=True, resource_type=resource_type)
        self.grid[center_x][center_y].cluster_id = cluster_id
        cluster_cells.append((center_x, center_y))
        
        # Special handling for water - create more linear patterns for rivers
        is_river = resource_type == "water" and random.random() < 0.7
        
        # Cells to process (cells that might spread to neighbors)
        cells_to_process = [(center_x, center_y)]
        
        # Initial spread probability
        spread_probability = density
        
        # For rivers, choose a primary direction
        if is_river:
            river_direction = random.choice([(0, 1), (1, 0), (1, 1), (-1, 1)])
            perpendicular = (river_direction[1], -river_direction[0])  # Perpendicular direction
        
        # Continue growing until we reach target size or run out of cells to process
        while cells_to_process and len(cluster_cells) < target_size:
            # Get next cell to process
            current_x, current_y = cells_to_process.pop(0)
            
            # Get valid neighboring cells
            neighbors = self._get_valid_neighbors(current_x, current_y)
            
            # If creating a river, prioritize neighbors in the river direction
            if is_river:
                neighbors.sort(key=lambda pos: self._river_priority(pos, 
                                                                   current_x, current_y, 
                                                                   river_direction, 
                                                                   perpendicular))
            
            # Try to spread to neighboring cells
            for nx, ny in neighbors:
                # Skip if already has resources
                if self.grid[nx][ny].has_resources() or (nx, ny) in cluster_cells:
                    continue
                
                # Determine if this cell becomes a resource based on probability
                # Probability decreases with distance from center for food
                # For water (rivers), maintain higher probability along the river direction
                if is_river:
                    # Higher probability in river direction, lower in perpendicular
                    dx, dy = nx - current_x, ny - current_y
                    align_with_river = abs(dx * river_direction[0] + dy * river_direction[1])
                    effective_probability = spread_probability * (1.0 if align_with_river else 0.3)
                else:
                    # Regular cluster with distance-based probability
                    distance = math.sqrt((nx - center_x)**2 + (ny - center_y)**2)
                    distance_factor = max(0.1, 1.0 - (distance / 10))
                    effective_probability = spread_probability * distance_factor
                
                if random.random() < effective_probability:
                    # Add resources to this cell
                    self.grid[nx][ny] = Cell(has_resources=True, resource_type=resource_type)
                    self.grid[nx][ny].cluster_id = cluster_id
                    cluster_cells.append((nx, ny))
                    cells_to_process.append((nx, ny))
                    
                    # Stop if we've reached the target size
                    if len(cluster_cells) >= target_size:
                        break
    
    def _river_priority(self, pos, x, y, river_dir, perp_dir):
        """
        Calculate priority for river growth. Higher priority = processed first.
        
        Args:
            pos: (nx, ny) position to evaluate
            x, y: Current position
            river_dir: Primary river direction
            perp_dir: Perpendicular direction (shores)
            
        Returns:
            float: Priority value (higher = processed first)
        """
        nx, ny = pos
        dx, dy = nx - x, ny - y
        
        # Alignment with river direction (dot product)
        river_alignment = dx * river_dir[0] + dy * river_dir[1]
        
        # Alignment with perpendicular (shore width)
        perp_alignment = dx * perp_dir[0] + dy * perp_dir[1]
        
        # Higher priority for river direction, lower for perpendicular
        if river_alignment > 0:
            return 2.0  # High priority for continuing river
        elif perp_alignment != 0:
            return 1.0  # Medium priority for shores
        else:
            return 0.5  # Low priority for other directions
    
    def _get_valid_neighbors(self, x, y):
        """
        Get valid neighboring cells (up, down, left, right, and diagonals).
        
        Args:
            x, y: Coordinates to find neighbors for
            
        Returns:
            list: List of (x,y) coordinates for valid neighbors
        """
        neighbors = []
        # Include diagonals for more natural growth
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip current cell
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    neighbors.append((nx, ny))
        return neighbors
    
    def _update_statistics(self):
        """Update statistics about the world's resources."""
        self.statistics = {
            'total_cells': self.width * self.height,
            'resource_cells': 0,
            'resource_by_type': {rtype: 0 for rtype in RESOURCE_TYPES}
        }
        
        # Count resources
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell.has_resources():
                    self.statistics['resource_cells'] += 1
                    if cell.resource_type:
                        self.statistics['resource_by_type'][cell.resource_type] += 1
        
        print(f"World initialized with {self.statistics['resource_cells']} resource cells")
        for rtype, count in self.statistics['resource_by_type'].items():
            if count > 0:
                print(f"  {rtype.capitalize()}: {count} cells")
    
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
    
    def has_resources(self, x, y, resource_type=None):
        """
        Check if the cell at the given position has resources.
        
        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.
            resource_type (str, optional): Specific resource type to check for.
            
        Returns:
            bool: True if the cell has resources (of the specified type if given), False otherwise.
        """
        cell = self.get_cell(x, y)
        if not cell:
            return False
            
        if resource_type:
            return cell.has_resources() and cell.resource_type == resource_type
        return cell.has_resources()
    
    def consume_resources(self, x, y):
        """
        Consume resources at the given position.
        
        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            tuple: (value, resource_type) where value is the amount obtained and
                   resource_type is the type of resource consumed ("food", "water", etc.)
        """
        cell = self.get_cell(x, y)
        if cell:
            return cell.consume()
        return 0, None
    
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
            'total': self.width * self.height,
            'by_type': {rtype: {'full': 0, 'regrowing': 0} for rtype in RESOURCE_TYPES}
        }
        
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell.state == Cell.STATE_FULL:
                    counts['full'] += 1
                    if cell.resource_type:
                        counts['by_type'][cell.resource_type]['full'] += 1
                elif cell.state == Cell.STATE_CONSUMED:
                    counts['consumed'] += 1
                elif cell.state == Cell.STATE_REGROWING:
                    counts['regrowing'] += 1
                    if cell.resource_type:
                        counts['by_type'][cell.resource_type]['regrowing'] += 1
        
        # Calculate percentages
        for key in ['full', 'consumed', 'regrowing']:
            counts[f'{key}_percent'] = (counts[key] / counts['total']) * 100
            
        return counts
    
    def get_nearest_resource(self, x, y, resource_type=None, max_distance=None):
        """
        Find the nearest resource of a specific type from a given position.
        
        Args:
            x, y: Starting coordinates
            resource_type: Type of resource to look for (None for any type)
            max_distance: Maximum search distance (None for unlimited)
            
        Returns:
            tuple: (distance, (resource_x, resource_y)) or (None, None) if not found
        """
        # Simple breadth-first search implementation
        visited = set([(x, y)])
        queue = [(x, y, 0)]  # (x, y, distance)
        
        while queue:
            cx, cy, distance = queue.pop(0)
            
            # Stop if we've reached maximum search distance
            if max_distance and distance > max_distance:
                break
                
            # Check if this cell has the resource we're looking for
            if self.has_resources(cx, cy, resource_type):
                return distance, (cx, cy)
                
            # Add unvisited neighbors to the queue
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue  # Skip current cell
                    nx, ny = cx + dx, cy + dy
                    if self.is_valid_position(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny, distance + 1))
                    
        # No resource found
        return None, None
    
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
                    if self.grid[nx][ny].has_resources():
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