"""
Simulation-wide tuning constants.
All values that affect gameplay, balance, or world generation live here.
"""

from pathlib import Path

# ── World generation ──────────────────────────────────────────────────────────

AGENT_COUNT = 8
NUM_SPRINGS = 3
CLIMATE_COARSE_SCALE = 50.0
CLIMATE_MEDIUM_SCALE = 20.0
TEMP_ELEVATION_COUPLING = 0.4

CLOUD_COUNT = 5
CLOUD_RADIUS_MIN = 8.0
CLOUD_RADIUS_MAX = 20.0
CLOUD_LIFESPAN_MIN = 150
CLOUD_LIFESPAN_MAX = 400
CLOUD_SPEED_MAX = 0.3
CLOUD_PRECIP_STRENGTH = 0.7
CLOUD_TEMP_REDUCTION = 0.25

TEMP_MIN_C = -10.0  # temperature at normalized value 0
TEMP_MAX_C = 40.0  # temperature at normalized value 1
DIURNAL_AMPLITUDE = 0.1  # normalized temperature swing peak-to-trough (= 5 °C)
PLANT_SHADE = 0.08  # normalized temp reduction on the plant tile (= 4 °C)
PLANT_SHADE_ADJACENT = (
    0.03  # normalized temp reduction on immediately adjacent tiles (= 1.5 °C)
)

ELEV_MAX_M = 2000  # elevation at normalized value 1 (metres)


def temp_to_c(t: float) -> float:
    return TEMP_MIN_C + t * (TEMP_MAX_C - TEMP_MIN_C)


# ── Agent lifecycle ───────────────────────────────────────────────────────────

MAX_AGE = 800
_MATURITY_FRACTION = 0.15  # adults at 15% of lifespan
MATURITY_AGE = int(MAX_AGE * _MATURITY_FRACTION)
VISION_RANGE = 20

# ── Needs & metabolism ────────────────────────────────────────────────────────

HUNGER_BASE_DRAIN = 0.01  # adult hunger drain per tick
HUNGER_INFANT_MULTIPLIER = 2.0  # infant drains this × base (scales to 1× at maturity)
HUNGER_RIVER_MULTIPLIER = 2.0  # river tile multiplies hunger drain
EAT_RESTORE = 0.20  # hunger restored per meal (~5 meals to go 0 → full)

WATER_BASE_DRAIN = 0.01
WATER_URGENCY_DISTANCE_SCALE = 15.0  # tiles at which comfort reaches ~60% (asymptotic)
WATER_LOST_URGENCY_MULTIPLIER = 3.0  # urgency multiplier when no water source is known
DRINK_RESTORE = 0.20  # water restored per drink (~5 drinks to go 0 → full)

REST_BASE_DRAIN = 0.005
REST_NIGHT_MULTIPLIER = 3.0  # drain multiplier while awake at night
REST_COLD_MULTIPLIER = (
    2.0  # drain multiplier at minimum temperature (scales to 1× at max temp)
)
REST_RESTORE_MIN = 0.005  # restore per tick on worst rest tile
REST_RESTORE_MAX = 0.025  # restore per tick on best rest tile

# ── Rest spot quality ─────────────────────────────────────────────────────────

REST_NOISE_WEIGHT = 0.5  # contribution from spatial noise
REST_RIVER_WEIGHT = 0.3  # bonus for proximity to river
REST_FOOD_WEIGHT = 0.2  # bonus for proximity to food
REST_SPOT_SEEK_THRESHOLD = 0.35  # min visible quality worth navigating toward
MEMORY_REST_BONUS = (
    0.15  # quality bonus for a remembered rest tile, decays with distance
)
REST_SAFETY_BUFFER_FRAC = 0.05  # rest fraction to keep in reserve when planning travel

# ── Reproduction ──────────────────────────────────────────────────────────────

REPRODUCTION_HUNGER_THRESHOLD = 0.85  # hunger [0,1] required to mate
REPRODUCTION_CHANCE = 0.07
REPRODUCTION_RANGE = 3  # manhattan distance within which mating can occur
MATING_COOLDOWN = 10  # ticks an agent must wait before mating again

# ── Decision making ───────────────────────────────────────────────────────────

CONTINUATION_BONUS = 0.15  # urgency bonus for staying on the current task
HARVEST_COST: dict[str, int] = {
    "date_palm": 6,
    "wild_plum": 2,
    "fig_tree": 4,
    "berry_bush": 3,
    "bilberry": 5,
}
HARVEST_CONTINUATION_BONUS = 0.25
DECISION_STRIDE = 2  # ticks between full agent decisions
PLAN_HORIZON = 2  # steps produced per decision

# ── Movement ─────────────────────────────────────────────────────────────────

FOOD_BASE_WEIGHT = 4.0
FOOD_HUNGER_BONUS = 4.0
FOOD_MEMORY_WEIGHT = 1.5
WANDER_WEIGHT = 0.15
MOMENTUM_WEIGHT = 0.3

# ── Ecology ───────────────────────────────────────────────────────────────────

RIVER_GRAVITY_SCALE = 10.0  # exp scale for elevation-based flow weighting
RIVER_DIRECTION_BIAS = 0.1  # effective-delta bonus for continuing in the same direction
RIVER_POOL_RISE_RATE = 0.01  # elevation units the pool fills per tick at a local min

HILL_COST_SCALE = 3.0  # extra A* cost per unit of elevation gained
RIVER_CROSSING_COST = 3.0  # extra A* cost for stepping onto a river tile
HILL_ENERGY_MULTIPLIER = (
    20.0  # uphill hunger drain = elev_gain × this × HUNGER_BASE_DRAIN
)

# ── Genetics & mutations ──────────────────────────────────────────────────────

SPONTANEOUS_MUTATION_RATE = 0.15
VISION_BOOST = 8  # vision range added by keen_sight mutation
VISION_PENALTY = 6  # vision range removed by poor_sight mutation
SEED_HETEROZYGOUS_RATE = 0.25
SEED_HOMOZYGOUS_RATE = 0.05

# ── Memory ────────────────────────────────────────────────────────────────────

MEMORY_CAP = 10
CONFIDENCE_PRUNE = 0.05
DECAY_RATE = 0.001
FAMILIARITY_WEIGHT = 0.2  # log-tapered bonus per revisit to a rest tile

# ── Metrics & logging ─────────────────────────────────────────────────────────

BIRTH_RATE_WINDOW = 20
LOGS_DIR = Path(__file__).parent.parent / "logs"

# ── Runtime overrides ─────────────────────────────────────────────────────────

import sys as _sys

_saved: dict = {}


def apply_runtime(**kwargs) -> None:
    """Override module-level constants for the current run (call before game start)."""
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
        module.MATURITY_AGE = int(module.MAX_AGE * _MATURITY_FRACTION)


def reset_runtime() -> None:
    """Restore all constants to their original values (call on game stop)."""
    module = _sys.modules[__name__]
    for name, value in _saved.items():
        setattr(module, name, value)
    _saved.clear()
