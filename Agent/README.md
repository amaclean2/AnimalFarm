# Agent Module

This module contains the Agent class for the AnimalFarm simulation.

## Structure

- `Agent.py` - Main Agent class implementation
- `__init__.py` - Package initialization file
- `test_agent.py` - Comprehensive unit tests for Agent lifecycle

## Running Tests

From the repository root:
```bash
python3 -m unittest Agent.test_agent -v
```

From within the Agent directory:
```bash
python3 -m unittest test_agent -v
```

## Test Coverage

The test suite includes 24 tests covering:
- Agent initialization (2 tests)
- Tick lifecycle mechanism (4 tests)
- Death conditions (2 tests)
- Reproduction lifecycle and constraints (7 tests)
- Eating and energy management (4 tests)
- Movement (2 tests)
- Complete lifecycle integration (3 tests)
