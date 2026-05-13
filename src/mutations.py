import random

from agent import Agent, VISION_RANGE, MAX_REST, REST_THRESHOLD_DEFAULT, NIGHT_DRAIN_DEFAULT

SPONTANEOUS_MUTATION_RATE = 0.15
VISION_BOOST = 8
VISION_PENALTY = 6

_MUTATIONS: dict[str, dict] = {
    "keen_sight": {"vision_range": VISION_RANGE + VISION_BOOST},
    "poor_sight": {"vision_range": max(1, VISION_RANGE - VISION_PENALTY)},
    "slow_metabolism": {"metabolism": 0.6},
    "fast_metabolism": {"metabolism": 1.5},
    "light_sleeper": {"rest_threshold": max(0, REST_THRESHOLD_DEFAULT - 15)},
    "heavy_sleeper": {"rest_threshold": min(MAX_REST, REST_THRESHOLD_DEFAULT + 25)},
    "night_owl": {"night_drain": 1},
}

MUTATION_NAMES = list(_MUTATIONS.keys())

SEED_HETEROZYGOUS_RATE = 0.25
SEED_HOMOZYGOUS_RATE = 0.05


def seed_genotype(agent: Agent) -> None:
    """Give a founding agent random alleles to bootstrap the gene pool."""
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
    """Alleles a parent with `count` recessive copies contributes to a child."""
    if count == 0:
        return 0
    if count == 2:
        return 1
    # Heterozygous carrier (Aa): 50% chance of passing the recessive allele
    return 1 if random.random() < 0.5 else 0


def apply_expressed_mutations(agent: Agent) -> None:
    """Reset phenotype to defaults, then express all homozygous-recessive (aa) loci."""
    agent.vision_range = VISION_RANGE
    agent.metabolism = 1.0
    agent.rest_threshold = REST_THRESHOLD_DEFAULT
    agent.night_drain = NIGHT_DRAIN_DEFAULT
    agent.mutations = [
        locus for locus, count in sorted(agent.genotype.items())
        if count == 2 and locus in _MUTATIONS
    ]
    for locus in agent.mutations:
        for attr, value in _MUTATIONS[locus].items():
            setattr(agent, attr, value)


def inherit_or_mutate(agent: Agent, parent_a: Agent, parent_b: Agent) -> None:
    """Build child genotype via Mendelian inheritance, then optionally add a spontaneous allele."""
    genotype: dict[str, int] = {}
    for locus in set(parent_a.genotype) | set(parent_b.genotype):
        child_alleles = (
            _alleles_passed(parent_a.genotype.get(locus, 0))
            + _alleles_passed(parent_b.genotype.get(locus, 0))
        )
        if child_alleles > 0:
            genotype[locus] = child_alleles

    if random.random() < SPONTANEOUS_MUTATION_RATE:
        locus = random.choice(MUTATION_NAMES)
        genotype[locus] = min(2, genotype.get(locus, 0) + 1)

    agent.genotype = genotype
    apply_expressed_mutations(agent)
