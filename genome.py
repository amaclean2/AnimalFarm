import random

IDLE_THRESHOLD = 0.25
BREAKAWAY_MARGIN = 0.20
REST_SEEK_THRESHOLD = 0.8

HUNGER_BASE_DRAIN = 0.01
WATER_BASE_DRAIN = 0.01
REST_BASE_DRAIN = 0.003

VISION_RANGE = 20

GENE_RANGES: dict[str, tuple[float, float]] = {
    "idle_threshold": (0.02, 0.40),
    "breakaway_margin": (0.05, 0.50),
    "rest_seek_threshold": (0.5, 0.95),
    "hunger_drain_rate": (0.003, 0.015),
    "water_drain_rate": (0.003, 0.015),
    "rest_drain_rate": (0.001, 0.010),
    "vision": (5.0, 40.0),
}

GENE_DEFAULTS: dict[str, float] = {
    "idle_threshold": IDLE_THRESHOLD,
    "breakaway_margin": BREAKAWAY_MARGIN,
    "rest_seek_threshold": REST_SEEK_THRESHOLD,
    "hunger_drain_rate": HUNGER_BASE_DRAIN,
    "water_drain_rate": WATER_BASE_DRAIN,
    "rest_drain_rate": REST_BASE_DRAIN,
    "vision": float(VISION_RANGE),
}


def default_genome() -> dict[str, float]:
    return dict(GENE_DEFAULTS)


def random_genome() -> dict[str, float]:
    return {gene: random.uniform(lo, hi) for gene, (lo, hi) in GENE_RANGES.items()}


def clamp_genome(genome: dict[str, float]) -> dict[str, float]:
    return {
        gene: max(lo, min(hi, genome.get(gene, GENE_DEFAULTS[gene])))
        for gene, (lo, hi) in GENE_RANGES.items()
    }


def crossover(
    genome_a: dict[str, float], genome_b: dict[str, float]
) -> dict[str, float]:
    return {
        gene: (genome_a[gene] if random.random() < 0.5 else genome_b[gene])
        for gene in GENE_RANGES
    }


def mutate(genome: dict[str, float], mutation_rate: float) -> dict[str, float]:
    result: dict[str, float] = {}

    for gene, value in genome.items():
        if random.random() < mutation_rate:
            value = value + random.gauss(0, value * 0.10)
        lo, hi = GENE_RANGES.get(gene, (value, value))
        result[gene] = max(lo, min(hi, value))
    return result


def apply_to_agent(agent, genome: dict[str, float]) -> None:
    agent.needs.hunger_drain_rate = genome["hunger_drain_rate"]
    agent.needs.water_drain_rate = genome["water_drain_rate"]
    agent.needs.rest_drain_rate = genome["rest_drain_rate"]
    agent.vision_range = round(genome["vision"])
