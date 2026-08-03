"""
Simulation-wide tuning constants.
All values that affect gameplay, balance, or world generation live here.
"""

from pathlib import Path

WORLD_WIDTH = 100
WORLD_HEIGHT = 100

AGENT_COUNT = 8
NUM_SPRINGS = 3
CLIMATE_COARSE_SCALE = 50.0
CLIMATE_MEDIUM_SCALE = 20.0
TEMP_ELEVATION_COUPLING = 0.4

TEMP_MIN_C = -10.0
TEMP_MAX_C = 40.0
DIURNAL_AMPLITUDE = 0.15
PLANT_SHADE = 0.08
PLANT_SHADE_ADJACENT = 0.03

ELEV_MAX_M = 2000


def temp_to_c(t: float) -> float:
    return TEMP_MIN_C + t * (TEMP_MAX_C - TEMP_MIN_C)


MAX_AGE = 800
MATURITY_FRACTION = 0.15
MATURITY_AGE = int(MAX_AGE * MATURITY_FRACTION)


INFANT_DRAIN_PENALTY = 3.0
HUNGER_RIVER_MULTIPLIER = 2.0

DRINK_RESTORE = 0.20

IDEAL_CORE_TEMP_C = 15.0
CORE_TEMP_DEATH_MARGIN_C = 5.0
CORE_TEMP_DRIFT_RATE = 0.001

INVENTORY_CAPACITY = 5

HEAT_THIRST_MULTIPLIER = 2.0
TILE_REST_RESTORE_MIN = 0.005
TILE_REST_RESTORE_MAX = 0.025

DRAIN_RATE_MULTIPLIER = 1.0  # speeds up or slows down all the drain rates together

# ── Rest spot quality ─────────────────────────────────────────────────────────

REST_NOISE_WEIGHT = 0.5  # contribution from spatial noise
REST_RIVER_WEIGHT = 0.3  # bonus for proximity to river
REST_FOOD_WEIGHT = 0.2  # bonus for proximity to food
REST_SPOT_SEEK_THRESHOLD = 0.35  # min visible quality worth navigating toward
MEMORY_REST_BONUS = (
    0.15  # quality bonus for a remembered rest tile, decays with distance
)

# ── Reproduction ──────────────────────────────────────────────────────────────

REPRODUCTION_CHANCE = 0.07
REPRODUCTION_RANGE = 1
MATING_COOLDOWN = 50

# ── Decision making ───────────────────────────────────────────────────────────

DECISION_STRIDE = 2  # ticks between full agent decisions
PLAN_HORIZON = 2  # steps produced per decision

# ── Ecology ───────────────────────────────────────────────────────────────────

RIVER_GRAVITY_SCALE = 10.0  # exp scale for elevation-based flow weighting
RIVER_DIRECTION_BIAS = 0.1  # effective-delta bonus for continuing in the same direction
RIVER_POOL_RISE_RATE = 0.01  # elevation units the pool fills per tick at a local min

HILL_COST_SCALE = 3.0  # extra A* cost per unit of elevation gained
RIVER_CROSSING_COST = 3.0  # extra A* cost for stepping onto a river tile
HILL_ENERGY_MULTIPLIER = (
    20.0  # uphill hunger drain = elev_gain × this × agent's hunger_drain_rate
)

# ── Genetics & mutations ──────────────────────────────────────────────────────

SPONTANEOUS_MUTATION_RATE = 0.15

# ── Behavioural evolution ─────────────────────────────────────────────────────

POOL_SEED_THRESHOLD = 50  # min pool rows before seeding new sims from elite
OFFSPRING_WEIGHT = 2.0  # fitness = lifespan * (1 + offspring * this)
DATA_DIR = Path(__file__).parent / "data"

# ── Memory ────────────────────────────────────────────────────────────────────

CROWD_CHECK_RADIUS = 3

LOGS_DIR = Path(__file__).parent / "logs"
DEBUG_HARVEST = True  # set False to disable harvest debug logging

# ── Runtime overrides ─────────────────────────────────────────────────────────

import sys as _sys

_saved: dict = {}


def apply_runtime(**kwargs) -> None:
    module = _sys.modules[__name__]
    for name, value in kwargs.items():
        if value is None or not hasattr(module, name):
            continue
        if name not in _saved:
            _saved[name] = getattr(module, name)
        setattr(module, name, value)

    if "MAX_AGE" in kwargs:
        if "MATURITY_AGE" not in _saved:
            _saved["MATURITY_AGE"] = module.MATURITY_AGE
        module.MATURITY_AGE = int(module.MAX_AGE * MATURITY_FRACTION)


def reset_runtime() -> None:
    module = _sys.modules[__name__]
    for name, value in _saved.items():
        setattr(module, name, value)
    _saved.clear()
