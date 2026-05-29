"""
Simulation-wide tuning constants.
All values that affect gameplay, balance, or world generation live here.
"""

from pathlib import Path

# ── World generation ──────────────────────────────────────────────────────────

AGENT_COUNT = 20
NUM_SPRINGS = 2
NUM_FOOD_CLUSTERS = 4
CLUSTER_SIGMA = 6.0
FOOD_PEAK_PROBABILITY = 0.5

# ── Agent lifecycle ───────────────────────────────────────────────────────────

MAX_AGE = 800
_MATURITY_FRACTION = 0.15  # adults at 15% of lifespan
MATURITY_AGE = int(MAX_AGE * _MATURITY_FRACTION)
VISION_RANGE = 20

# ── Needs & metabolism ────────────────────────────────────────────────────────

MAX_HUNGER = 100
MAX_WATER = 100
MAX_REST = 100
MAX_WARMTH = 1.0

ADULT_DRAIN = 1  # hunger drained per tick (adult)
INFANT_DRAIN = 2  # hunger drained per tick (infant, scales with age toward ADULT_DRAIN)
EAT_RESTORE = 20  # hunger restored per meal (~4 meals to go 0 → full)

WATER_DRAIN = 1
DRINK_RESTORE = 20  # water restored per drink (~4 drinks to go 0 → full)
WATER_DRAIN_MULTIPLIER = 2  # extra hunger penalty when standing on a river tile

REST_DRAIN = 1
REST_RESTORE = 3
REST_THRESHOLD = 40  # rest level at which agent falls asleep
NIGHT_DRAIN = 3  # rest drained per tick while awake at night

WARMTH_EXPOSED_DRAIN = 0.05
WARMTH_SHELTERED_DRAIN = 0.01
WARMTH_RESTORE = 0.03

LONE_HUNGER_PENALTY = 1  # extra hunger drain per tick when not in a group
SLEEP_HUNGER_OVERRIDE = 60  # agent wakes if hunger drops below this even while sleeping

# ── Reproduction ──────────────────────────────────────────────────────────────

REPRODUCTION_HUNGER_THRESHOLD = 0.87  # fraction of MAX_HUNGER required to mate
REPRODUCTION_CHANCE = 0.05
REPRODUCTION_RANGE = 3  # manhattan distance within which mating can occur

# ── Decision making ───────────────────────────────────────────────────────────

CONTINUATION_BONUS = 0.15  # urgency bonus for staying on the current task

# ── Movement ─────────────────────────────────────────────────────────────────

FOOD_BASE_WEIGHT = 4.0
FOOD_HUNGER_BONUS = 4.0
FOOD_MEMORY_WEIGHT = 1.5
SOCIAL_COHESION_WEIGHT = 2.0
SOCIAL_FRINGE_WEIGHT = 4.0
SOCIAL_LONE_WEIGHT = 1.5
WANDER_WEIGHT = 0.15
MOMENTUM_WEIGHT = 0.3

# ── Groups ────────────────────────────────────────────────────────────────────

BASE_GRAVITY = 1.0
BASE_COHESION = 5.0
ATTRACTION_MULTIPLIER = 2.0
VISION_BONUS = 1.5  # vision range multiplier when inside group cohesion radius

# ── Ecology ───────────────────────────────────────────────────────────────────

FOOD_REGROW_TICKS = 40
FOOD_SPREAD_SIGMA = 20.0
FOOD_SPREAD_CANDIDATES = 50
FOOD_WATER_WEIGHT = 2.0
FOOD_CLUSTER_WEIGHT = 1.0
FOOD_SCORE_FLOOR = 0.01

RIVER_DOWN_WEIGHT = 3.0
RIVER_LATERAL_WEIGHT = 2.0
RIVER_UP_WEIGHT = 0.5

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
