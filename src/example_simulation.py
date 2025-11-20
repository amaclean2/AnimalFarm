#!/usr/bin/env python
"""
Example simulation demonstrating the Animal Farm simulation loop and metrics tracking.

This script creates a simple simulation and runs it for a specified number of ticks,
printing out metrics at regular intervals.
"""

import sys
import os

# Ensure imports work properly
sys.path.append(os.path.dirname(__file__))

from simulation import Simulation
from World.world import World
from World.resources import ResourceManager

def main():
  # Configuration
  WORLD_WIDTH = 100
  WORLD_HEIGHT = 100
  INITIAL_POPULATION = 50
  INITIAL_FOOD = 500
  FOOD_REGEN_RATE = 0.01
  NUM_TICKS = 500
  REPORT_INTERVAL = 50
  
  print("=== Animal Farm Simulation ===")
  print(f"World Size: {WORLD_WIDTH}x{WORLD_HEIGHT}")
  print(f"Initial Population: {INITIAL_POPULATION}")
  print(f"Initial Food: {INITIAL_FOOD}")
  print(f"Food Regeneration Rate: {FOOD_REGEN_RATE}")
  print(f"Simulation Duration: {NUM_TICKS} ticks")
  print()
  
  # Initialize world and resources
  world = World(width=WORLD_WIDTH, height=WORLD_HEIGHT)
  resource_manager = ResourceManager(
    world, 
    initial_food_count=INITIAL_FOOD,
    regen_rate=FOOD_REGEN_RATE
  )
  
  # Initialize simulation
  sim = Simulation(world, resource_manager, initial_population=INITIAL_POPULATION)
  
  print("Starting simulation...")
  print()
  
  # Run simulation with periodic reporting
  for tick in range(NUM_TICKS):
    sim.tick()
    
    # Report metrics at intervals
    if (tick + 1) % REPORT_INTERVAL == 0:
      metrics = sim.get_metrics()
      print(f"Tick {tick + 1}:")
      print(f"  Population: {metrics['current_population']}")
      print(f"  Total Births: {metrics['total_births']}")
      print(f"  Total Deaths: {metrics['total_deaths']}")
      print(f"  Average Lifespan: {metrics['average_lifespan']:.2f}")
      print(f"  Food Available: {len(resource_manager.food_positions)}")
      print()
  
  # Final report
  print("=== Final Simulation Results ===")
  final_metrics = sim.get_metrics()
  print(f"Final Population: {final_metrics['current_population']}")
  print(f"Total Births: {final_metrics['total_births']}")
  print(f"Total Deaths: {final_metrics['total_deaths']}")
  print(f"Average Lifespan: {final_metrics['average_lifespan']:.2f}")
  print(f"Food Available: {len(resource_manager.food_positions)}")
  print()
  
  # Population stability check
  if final_metrics['current_population'] > 0:
    print("✓ Population survived the simulation period")
  else:
    print("✗ Population died out completely")
  
  # Show population trend
  population_history = final_metrics['population_history']
  if len(population_history) >= 2:
    start_pop = population_history[0]
    end_pop = population_history[-1]
    if end_pop > start_pop * 1.1:
      print("↗ Population is growing")
    elif end_pop < start_pop * 0.9:
      print("↘ Population is declining")
    else:
      print("→ Population is relatively stable")

if __name__ == '__main__':
  main()
