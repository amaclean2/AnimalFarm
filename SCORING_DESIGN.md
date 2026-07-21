# Scoring engine design (Phase 0 target)

This is the design for the refactored `choose_action`, the thing Phase 0 in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) builds toward. None of this exists yet. It's pseudocode based on the real structures in [agent.py](agents/agent.py), [needs.py](agents/needs.py), and [genome.py](genome.py).

## The core loop

Today, `choose_action` is a list of hardcoded `if ... return` checks, and only once none of them fire does real scoring happen. The target replaces that whole cascade with one registry of scorer functions, each one representing a single candidate action, all producing numbers on the same scale, with the winner picked by argmax.

```python
ScorerFn = Callable[[Agent, World], ScoredCandidate | None]

SCORERS: list[ScorerFn] = []

def register_scorer(fn: ScorerFn) -> ScorerFn:
    SCORERS.append(fn)
    return fn

def choose_action(agent: Agent, world: World) -> Task:
    candidates = [c for scorer in SCORERS if (c := scorer(agent, world)) is not None]
    best = max(candidates, key=lambda c: c.score)
    return Task(name=best.task_name, goal_pos=best.goal_pos)
```

A scorer returns `None` if the action isn't currently available (no known water source, no urgent need, nothing to harvest), and a score otherwise. There's no priority order between scorers and no early return. Whatever number comes out on top wins that tick.

Existing needs become scorers almost unchanged, since `calculate_urgencies` already computes the right numbers today, it's just gated behind the cascade instead of feeding straight into the registry:

```python
@register_scorer
def score_seek_water(agent, world):
    target = agent.memory.query("water", agent.pos)
    if target is None:
        return None
    urgency = (1.0 - agent.needs.water) ** 2
    ticks_left = agent.needs.get_ticks_to_empty("water")
    dist = manhattan(target, agent.pos)
    if dist + 2 >= ticks_left:
        urgency = 1.0
    return ScoredCandidate("seek_water", urgency, target)

@register_scorer
def score_sleep(agent, world):
    urgency = (1.0 - agent.needs.rest) ** 2
    return ScoredCandidate("sleep", urgency, agent.pos)
```

## Adding a new capability

A new capability is a new scorer function plus, usually, a new gene. Caching is a good example, since it doesn't exist today.

```python
@register_scorer
def score_cache_surplus(agent, world):
    propensity = agent.behavioral_genome["cache_propensity"]
    if propensity <= 0 or agent.needs.hunger < 0.9:
        return None
    return ScoredCandidate("cache_food", propensity * CACHE_BASE_VALUE, agent.pos)
```

That's the entire integration. `choose_action` doesn't change. Nothing that scores other actions needs to know caching exists. If caching is worth doing given the agent's current state and its gene, it shows up as a candidate and competes on its own merits. If it isn't worth doing, it returns `None` and never enters the running.

## Adding a new environmental constraint

A constraint never adds a scorer. It changes a number that scorers already read. Weather is the example already in the plan, a storm raising rest drain until shelter starts winning on its own.

```python
def apply_storm(world: World) -> None:
    world.rest_drain_multiplier = STORM_REST_DRAIN_MULTIPLIER
```

`score_sleep` and `score_seek_rest` don't need to know a storm is happening. They just read `agent.needs.get_ticks_to_empty("rest")`, which already factors in `world.rest_drain_multiplier` alongside the agent's own `rest_drain_rate` gene. Rest urgency climbs faster during a storm purely because its inputs changed, not because any scorer was told to treat storms specially. This is also why the multiplier lives on `world`, not on the gene itself. The gene is the agent's baseline tendency, and the environment is a separate multiplier layered on top of it, so a storm affects every agent's rest drain without touching anyone's genome.

## How genes come into it

Genes never appear inside `choose_action` logic itself. They're just numbers a scorer reads, exactly like `breakaway_margin` and `idle_threshold` are read today. A capability that wants to evolve gets its own gene the same way:

```python
GENE_RANGES["cache_propensity"] = (0.0, 1.0)
GENE_DEFAULTS["cache_propensity"] = 0.0
```

Evolution itself doesn't happen in the scorer at all. It happens where it already happens, in [genome.py](genome.py)'s `crossover`, `mutate`, and `clamp_genome`, and in `GenomePool.record` scoring agents on lifespan times offspring after the fact. An agent with a `cache_propensity` that happened to help it survive scarcity gets more offspring, and those offspring inherit genomes drawn from that success. The scorer for caching never changes. What changes over generations is only the distribution of `cache_propensity` values agents are born with, discovered by selection rather than tuned by hand.

So the full loop, end to end: a capability ships as a scorer plus a gene, an agent's gene value shapes what that scorer returns each tick, `choose_action` picks whichever candidate scores highest that tick with no knowledge of where the number came from, and over many generations `GenomePool` reshapes the population's gene values based on which ones led to more surviving offspring. Adding the next capability after that means writing one more function like the ones above, never touching `choose_action`.
