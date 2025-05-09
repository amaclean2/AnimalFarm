"""
Agent class for the Agent Survival Simulation.

The Agent class represents an entity that navigates the world, collects and consumes
resources, and attempts to survive as long as possible by managing its energy levels.
"""
import pygame
import random
import math
from config import (
    CELL_SIZE, COLOR, INITIAL_CALORIES, MAX_CALORIES,
    INITIAL_SLEEP, MAX_SLEEP, RESOURCE_SENSING_RANGE,
    OPTIMAL_CHOICE_PROBABILITY, SLEEP_ENERGY_GAIN,
    CALORIE_CONSUMPTION_PER_DAY, MOVES_PER_DAY,
    AGENT_COLORS, HOME_BASE_POSITION
)

class Agent:
    """
    Represents an intelligent agent that navigates the world, collects and consumes resources.
    
    The agent has two types of energy: calories for sustenance and sleep energy for activity.
    It must balance collecting food during the day and resting at night to survive.
    """
    
    # Define agent states
    STATE_ACTIVE = 0     # Agent is awake and moving/foraging
    STATE_RETURNING = 1  # Agent is returning to home base
    STATE_SLEEPING = 2   # Agent is sleeping
    STATE_DEAD = 3       # Agent is dead
    
    def __init__(self, x, y, agent_id="agent1"):
        """
        Initialize a new agent.
        
        Args:
            x (int): The initial x-coordinate of the agent.
            y (int): The initial y-coordinate of the agent.
            agent_id (str): Identifier for the agent, used for color and stats.
        """

        # Initialize agent position and state
        self.x = x
        self.y = y
        self.last_dx = 0
        self.last_dy = 0

        # Initialize agent ID
        self.agent_id = agent_id

        # Initialize agent energy levels
        self.calories = INITIAL_CALORIES
        self.max_calories = MAX_CALORIES
        self.collected_calories = 0
        self.sleep_energy = INITIAL_SLEEP
        self.max_sleep_energy = MAX_SLEEP

        # Initialize agent state variables
        self.alive = True
        self.is_sleeping = False
        self.state = self.STATE_ACTIVE
        self.days_survived = 0
        self.moves_today = 0
        
        # Distance traveled stats
        self.total_distance_traveled = 0
        
        # Home base coordinates
        self.home_x, self.home_y = HOME_BASE_POSITION
        
        # Path planning
        self.returning_home = False
        self.path_to_home = []
        
        print(f"Agent {agent_id} created at position ({x}, {y})")

    def update(self, world, is_day):
        """
        Update the agent based on the time of day and current state.
        
        Args:
            world (World): The world the agent is in.
            is_day (bool): Whether it is currently day.
            
        Returns:
            bool: True if the agent performed an action, False otherwise.
        """
        if not self.alive:
            return False
        
        if is_day:
            return self._update_daytime(world)
        else:
            return self._update_nighttime()
    
    def _update_daytime(self, world):
        """Handle daytime behavior: moving, collecting resources, or returning home."""
        # Calculate distance to home
        distance_to_home = self.get_distance_to_home()
        moves_remaining = MOVES_PER_DAY - self.moves_today
        
        # Determine if we need to start returning home
        if not self.returning_home and distance_to_home >= moves_remaining:
            self.returning_home = True
            self.state = self.STATE_RETURNING
            self._calculate_path_to_home()
            print(f"{self.agent_id} starting to return home with {moves_remaining} moves left")
        
        # Either continue foraging or return home
        if self.returning_home:
            result = self._move_towards_home(world)
        else:
            # Regular foraging
            if self.moves_today < MOVES_PER_DAY:
                result = self.move(world)
            else:
                result = False  # No more moves today
        
        # Update move counter if a move was made
        if result:
            self.moves_today += 1
        
        return result
    
    def _update_nighttime(self):
        """
        Eat collected calories and sleep (nighttime activity).
        
        Returns:
            bool: True if the agent performed an action, False if night routine is complete.
        """
        # Reset returning home state
        self.returning_home = False
        self.path_to_home = []
        
        if not self.is_sleeping:
            # First night cycle: eat calories
            self.consume_collected_calories()
            self.is_sleeping = True
            self.state = self.STATE_SLEEPING
            return True
        else:
            # Second+ night cycle: sleep to restore energy
            self.sleep()
            
            # If sleep is full, night is over
            if self.sleep_energy >= self.max_sleep_energy:
                self._wake_up()
                return False  # Night routine complete
            
            return True  # Still sleeping
    
    def get_distance_to_home(self):
        """Calculate Manhattan distance from current position to home base."""
        return abs(self.x - self.home_x) + abs(self.y - self.home_y)
    
    def _calculate_path_to_home(self):
        """Calculate a direct path to home base."""
        self.path_to_home = []
        
        # Calculate the number of steps in each direction
        dx = self.home_x - self.x
        dy = self.home_y - self.y
        
        # Create path by alternating x and y steps
        x, y = self.x, self.y
        
        # Handle x direction first
        steps_x = abs(dx)
        direction_x = 1 if dx > 0 else -1
        
        for _ in range(steps_x):
            x += direction_x
            self.path_to_home.append((x, y))
        
        # Then handle y direction
        steps_y = abs(dy)
        direction_y = 1 if dy > 0 else -1
        
        for _ in range(steps_y):
            y += direction_y
            self.path_to_home.append((x, y))
    
    def _move_towards_home(self, world):
        """Move along the calculated path to home."""
        if not self.path_to_home:
            # Already at home or no path calculated
            self.returning_home = False
            return False
        
        # Get the next step in the path
        next_x, next_y = self.path_to_home[0]
        
        # Check if the move is valid
        if world.is_valid_position(next_x, next_y):
            # Calculate movement direction for animation
            self.last_dx = next_x - self.x
            self.last_dy = next_y - self.y
            
            # Update position
            self.x, self.y = next_x, next_y
            
            # Remove this step from the path
            self.path_to_home.pop(0)
            
            # Moving costs sleep energy
            self.sleep_energy -= 1
            
            # Check if agent is still alive
            if self.sleep_energy <= 0:
                self._die()
                return False
                
            # Consume resources if we landed on a resource cell
            calories_gained = world.consume_resources(self.x, self.y)
            self.collected_calories += calories_gained
            
            # Check if we've reached home
            if self.x == self.home_x and self.y == self.home_y:
                self.returning_home = False
                self.path_to_home = []
                print(f"{self.agent_id} has reached home with {MOVES_PER_DAY - self.moves_today} moves left")
            
            return True
        else:
            # Invalid move, recalculate path
            self._calculate_path_to_home()
            return False
    
    def move(self, world):
        """
        Move the agent to collect calories (daytime activity).
        
        Args:
            world (World): The world the agent is in.
            
        Returns:
            bool: True if the agent moved, False otherwise.
        """
        # Get new movement direction
        new_x, new_y = self.calculate_movement(world)
        
        # Make sure the new position is valid
        if world.is_valid_position(new_x, new_y):
            self._perform_move(new_x, new_y, world)
            
            # Calculate distance traveled (Manhattan distance)
            distance = abs(new_x - self.x) + abs(new_y - self.y)
            self.total_distance_traveled += distance
            
            return True  # Made a move
        
        return False  # Couldn't move
    
    def _perform_move(self, new_x, new_y, world):
        """Execute the movement and handle consequences."""
        self.x = new_x
        self.y = new_y
        
        # Consume resources from the new cell
        calories_gained = world.consume_resources(self.x, self.y)
        self.collected_calories += calories_gained
        
        # Moving costs sleep energy
        self.sleep_energy -= 1
        
        # Check if agent is still alive
        if self.sleep_energy <= 0:
            self._die()        
    
    def _wake_up(self):
        """Wake up the agent at the start of a new day."""
        self.is_sleeping = False
        self.state = self.STATE_ACTIVE
        self.moves_today = 0  # Reset for the new day
        self.days_survived += 1  # Count a new day
    
    def consume_collected_calories(self):
        """Consume collected calories at night to maintain energy."""
        # Eat calories - either collected amount or daily requirement, whichever is less
        calories_to_eat = min(self.collected_calories, CALORIE_CONSUMPTION_PER_DAY)
        
        # Add to agent's energy reserves
        self.calories += calories_to_eat
        
        # Cap calories at maximum
        if self.calories > self.max_calories:
            self.calories = self.max_calories
            
        # Subtract consumed calories from collected
        self.collected_calories -= calories_to_eat
        
        # If didn't have enough calories, start dying
        if calories_to_eat < CALORIE_CONSUMPTION_PER_DAY:
            # Not enough food - burn reserves
            deficit = CALORIE_CONSUMPTION_PER_DAY - calories_to_eat
            self.calories -= deficit
            
            # Check if starved
            if self.calories <= 0:
                self._die()
    
    def _die(self):
        """Handle agent death."""
        self.alive = False
        self.state = self.STATE_DEAD
    
    def calculate_movement(self, world):
        """
        Calculate the next movement direction using resource sensing heuristic.
        
        Args:
            world (World): The world the agent is in.
            
        Returns:
            tuple: The new (x, y) position.
        """
        # First, scan the nearby cells for resources
        resource_directions = self._scan_for_resources(world)
        
        if resource_directions:
            return self._choose_resource_direction(resource_directions)
        else:
            return self._random_movement(world)
    
    def _scan_for_resources(self, world):
        """Scan the surrounding area for resources."""
        resource_directions = []
        scan_range = RESOURCE_SENSING_RANGE
        
        for dx in range(-scan_range, scan_range + 1):
            for dy in range(-scan_range, scan_range + 1):
                # Skip the current position
                if dx == 0 and dy == 0:
                    continue
                    
                # Calculate target position
                target_x = self.x + dx
                target_y = self.y + dy
                
                # Check if position is valid and has resources
                if world.has_resources(target_x, target_y):
                    # Calculate distance (Manhattan distance)
                    distance = abs(dx) + abs(dy)
                    
                    # Add to list of resource directions with weight inversely proportional to distance
                    weight = 1.0 / max(1, distance)
                    resource_directions.append((dx, dy, weight))
        
        return resource_directions
    
    def _choose_resource_direction(self, resource_directions):
        """Choose a direction to move based on resource locations."""
        # Sort by weight (higher weights first)
        resource_directions.sort(key=lambda x: x[2], reverse=True)
        
        # With probability OPTIMAL_CHOICE_PROBABILITY, move toward the highest-weighted resource
        # With remaining probability, pick a random direction from the resource list
        if random.random() < OPTIMAL_CHOICE_PROBABILITY:
            target_dx, target_dy, _ = resource_directions[0]
        else:
            target_dx, target_dy, _ = random.choice(resource_directions)
        
        # Normalize to single-step movement (-1, 0, or 1)
        dx = max(-1, min(1, target_dx))
        dy = max(-1, min(1, target_dy))
        
        # Calculate new position
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Update last movement for next iteration
        self.last_dx = dx
        self.last_dy = dy
        
        return new_x, new_y
    
    def _random_movement(self, world):
        """Generate random movement when no resources are visible."""
        # Generate a random movement direction
        random_dx = random.choice([-1, 0, 1])
        random_dy = random.choice([-1, 0, 1])
        
        # Handle wall collisions
        self._handle_wall_collisions(world)
        
        # Calculate average of last movement and new random movement
        avg_dx = (self.last_dx + random_dx) / 2
        avg_dy = (self.last_dy + random_dy) / 2
        
        # Convert floating point to integer direction
        dx = round(avg_dx)
        dy = round(avg_dy)
        
        # If both are zero, pick a random direction
        if dx == 0 and dy == 0:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            if dx == 0 and dy == 0:  # Ensure we're actually moving
                dx = random.choice([-1, 1])
        
        # Calculate new position
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Update last movement for next iteration
        self.last_dx = dx
        self.last_dy = dy
        
        return new_x, new_y
    
    def _handle_wall_collisions(self, world):
        """Handle collisions with world boundaries."""
        # Check if agent is against a wall and flip movement accordingly
        if self.x == 0:  # Left wall
            if self.last_dx < 0:
                self.last_dx = -self.last_dx  # Flip direction
        elif self.x == world.width - 1:  # Right wall
            if self.last_dx > 0:
                self.last_dx = -self.last_dx  # Flip direction
                
        if self.y == 0:  # Top wall
            if self.last_dy < 0:
                self.last_dy = -self.last_dy  # Flip direction
        elif self.y == world.height - 1:  # Bottom wall
            if self.last_dy > 0:
                self.last_dy = -self.last_dy  # Flip direction
    
    def sleep(self):
        """Sleep to restore energy."""
        # Gain sleep energy
        self.sleep_energy += SLEEP_ENERGY_GAIN
        
        # Cap sleep energy at maximum
        if self.sleep_energy > self.max_sleep_energy:
            self.sleep_energy = self.max_sleep_energy
    
    def is_at_home(self):
        """Check if the agent is currently at the home base."""
        return self.x == self.home_x and self.y == self.home_y
    
    def get_state_description(self):
        """Get a textual description of the agent's current state."""
        if self.state == self.STATE_ACTIVE:
            return "Foraging"
        elif self.state == self.STATE_RETURNING:
            return "Returning Home"
        elif self.state == self.STATE_SLEEPING:
            return "Sleeping"
        elif self.state == self.STATE_DEAD:
            return "Dead"
        return "Unknown"
    
    def draw(self, screen, camera=None):
        """
        Draw the agent on the screen.
        
        Args:
            screen: The pygame screen to draw on.
            camera (Camera): Camera used for viewport rendering.
        """
        # Get screen position
        screen_pos = self._get_screen_position(camera)
        if not screen_pos:
            return
            
        center_x, center_y = screen_pos
        radius = CELL_SIZE // 2 - 2
        
        # Draw components
        if self.state == self.STATE_ACTIVE:
            self._draw_sensing_range(screen, center_x, center_y)
        
        self._draw_agent_body(screen, center_x, center_y, radius)
        
        # Draw direction indicator
        if (self.state == self.STATE_ACTIVE or self.state == self.STATE_RETURNING) and (self.last_dx != 0 or self.last_dy != 0):
            self._draw_direction_indicator(screen, center_x, center_y, radius)
    
    def _get_screen_position(self, camera):
        """Calculate the screen position considering the camera."""
        # If the agent is not visible in the camera viewport, don't draw
        if camera and not camera.is_visible(self.x, self.y):
            return None
            
        # Get screen coordinates for the agent
        if camera:
            screen_pos = camera.world_to_screen(self.x, self.y)
            if not screen_pos:
                return None
            
            center_x = screen_pos[0] * CELL_SIZE + CELL_SIZE // 2
            center_y = screen_pos[1] * CELL_SIZE + CELL_SIZE // 2
        else:
            center_x = self.x * CELL_SIZE + CELL_SIZE // 2
            center_y = self.y * CELL_SIZE + CELL_SIZE // 2
            
        return center_x, center_y
    
    def _draw_sensing_range(self, screen, center_x, center_y):
        """Draw the agent's sensing range."""
        # Calculate visible sensing range in the viewport
        sensing_radius = min(RESOURCE_SENSING_RANGE, 4) * CELL_SIZE
        sensing_surface = pygame.Surface((sensing_radius * 2, sensing_radius * 2), pygame.SRCALPHA)
        
        pygame.draw.circle(sensing_surface, COLOR['TRANSPARENT_YELLOW'], 
                         (sensing_radius, sensing_radius), sensing_radius)
        screen.blit(sensing_surface, (center_x - sensing_radius, center_y - sensing_radius))
    
    def _draw_agent_body(self, screen, center_x, center_y, radius):
        """Draw the agent's body."""
        # Draw agent circle with color based on agent ID and state
        if self.state == self.STATE_SLEEPING:
            agent_color = AGENT_COLORS[self.agent_id]['asleep']
        elif self.state == self.STATE_RETURNING:
            # Use a darker shade of the agent's color for returning home
            base_color = AGENT_COLORS[self.agent_id]['awake']
            agent_color = (base_color[0] // 2, base_color[1] // 2, base_color[2] // 2)
        else:
            agent_color = AGENT_COLORS[self.agent_id]['awake']
            
        pygame.draw.circle(screen, agent_color, (center_x, center_y), radius)
        
        # If returning home, add a small indicator
        if self.state == self.STATE_RETURNING:
            # Draw a small home indicator in the center
            indicator_size = radius // 2
            pygame.draw.rect(screen, COLOR['YELLOW'], 
                           (center_x - indicator_size//2, center_y - indicator_size//2, 
                            indicator_size, indicator_size))
    
    def _draw_direction_indicator(self, screen, center_x, center_y, radius):
        """Draw an indicator showing the agent's movement direction."""
        end_x = center_x + self.last_dx * radius * 0.6
        end_y = center_y + self.last_dy * radius * 0.6
        pygame.draw.line(screen, COLOR['YELLOW'], (center_x, center_y), (end_x, end_y), 3)