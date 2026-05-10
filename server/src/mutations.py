import random

from agent import Agent, VISION_RANGE

MUTATION_RATE = 0.2
VISION_BOOST = 8
VISION_PENALTY = 6

_MUTATIONS: dict[str, dict] = {
    "keen_sight": {"vision_range": VISION_RANGE + VISION_BOOST},
    "poor_sight": {"vision_range": max(1, VISION_RANGE - VISION_PENALTY)},
    "slow_metabolism": {"metabolism": 0.6},
    "fast_metabolism": {"metabolism": 1.5},
}

MUTATION_NAMES = list(_MUTATIONS.keys())


def apply_mutation(agent: Agent) -> None:
    if random.random() >= MUTATION_RATE:
        return
    name = random.choice(MUTATION_NAMES)
    agent.mutation = name
    for attr, value in _MUTATIONS[name].items():
        setattr(agent, attr, value)
