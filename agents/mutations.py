import random

import config as _cfg
from config import (
    VISION_RANGE,
    REST_NIGHT_MULTIPLIER,
    VISION_BOOST,
    VISION_PENALTY,
    SEED_HETEROZYGOUS_RATE,
    SEED_HOMOZYGOUS_RATE,
)

_MUTATIONS: dict[str, dict] = {
    "keen_sight": {"vision_range": VISION_RANGE + VISION_BOOST},
    "poor_sight": {"vision_range": max(1, VISION_RANGE - VISION_PENALTY)},
    "slow_metabolism": {"metabolism": 0.6},
    "fast_metabolism": {"metabolism": 1.5},
    "night_owl": {"night_drain_multiplier": 1.0},
}

MUTATION_NAMES = list(_MUTATIONS.keys())

_NEEDS_ATTRS = {"metabolism", "night_drain_multiplier"}


def seed_genotype(agent) -> None:
    genotype: dict[str, int] = {}
    for locus in MUTATION_NAMES:
        roll = random.random()
        if roll < SEED_HOMOZYGOUS_RATE:
            genotype[locus] = 2
        elif roll < SEED_HOMOZYGOUS_RATE + SEED_HETEROZYGOUS_RATE:
            genotype[locus] = 1
    agent.genotype = genotype
    apply_expressed_mutations(agent)


def _alleles_passed(count: int) -> int:
    if count == 0:
        return 0
    if count == 2:
        return 1
    return 1 if random.random() < 0.5 else 0


def apply_expressed_mutations(agent) -> None:
    agent.vision_range = VISION_RANGE
    agent.needs.metabolism = agent.behavioral_genome.get("metabolism", 1.0)
    agent.needs.night_drain_multiplier = REST_NIGHT_MULTIPLIER

    agent.mutations = [
        locus
        for locus, count in sorted(agent.genotype.items())
        if count == 2 and locus in _MUTATIONS
    ]
    for locus in agent.mutations:
        for attr, value in _MUTATIONS[locus].items():
            if attr in _NEEDS_ATTRS:
                setattr(agent.needs, attr, value)
            else:
                setattr(agent, attr, value)


def inherit_or_mutate(agent, parent_a, parent_b) -> None:
    genotype: dict[str, int] = {}
    for locus in set(parent_a.genotype) | set(parent_b.genotype):
        child_alleles = _alleles_passed(
            parent_a.genotype.get(locus, 0)
        ) + _alleles_passed(parent_b.genotype.get(locus, 0))
        if child_alleles > 0:
            genotype[locus] = child_alleles

    if random.random() < _cfg.SPONTANEOUS_MUTATION_RATE:
        locus = random.choice(MUTATION_NAMES)
        genotype[locus] = min(2, genotype.get(locus, 0) + 1)

    agent.genotype = genotype
    apply_expressed_mutations(agent)
