# Agent Survival Simulation

A simulation of an agent navigating a resource-constrained environment with day-night cycles and energy management.

## Overview

This simulation models an agent that must gather resources during the day and sleep at night. The agent has two energy systems: calories for sustenance and sleep energy for activity. The agent must balance exploration, resource collection, and rest to survive as long as possible.

## Features

- **Day-Night Cycle**: The agent makes a set number of moves during the day, then sleeps at night
- **Resource Management**: Agent must collect enough food each day to sustain itself
- **Energy Systems**: Dual energy system with calories and sleep
- **Resource Sensing**: Agent can detect nearby resources and move toward them
- **Visual Feedback**: Clean visualization with status panel and sensing radius

## Controls

- **Space**: Pause/resume the simulation
- **R**: Restart the simulation
- **Escape**: Exit the simulation

## How to Run

1. Ensure you have Python 3.6+ and Pygame installed
2. Run `python main.py` to start the simulation

## Configuration

You can modify various simulation parameters in `config.py`:

- Agent properties (initial energy, sensing range, etc.)
- World properties (size, initial resource percentage)
- Display settings (colors, cell size, FPS)
- Game mechanics (moves per day, daily calorie consumption)

## Project Structure

- `config.py`: Central configuration for the simulation
- `main.py`: Entry point for the application
- `models/`: Contains the core simulation classes (agent, cell, world)
- `visualization/`: Handles rendering and UI elements
- `simulation/`: Manages game state and logic

## License

This project is open source and available under the MIT License.
