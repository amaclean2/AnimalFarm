# Agent Design

## Vision

Agents should emerge as credible actors in a world they genuinely have to survive. The goal is not to script behaviors but to give agents enough structure that interesting behavior emerges naturally as the world grows more complex.

The development path follows Maslow's hierarchy: agents first learn to meet survival needs instinctively, then develop competence through repeated action, then form cooperative relationships, and eventually participate in market economies. Each phase depends on the previous being genuinely established. Agents can't trade what they don't have, and they won't specialize in what doesn't matter for survival.

## Architecture

Each agent is composed of three collaborating classes:

- **`NeedState`** — owns physiological state and urgency computation. Driven by simulation events (drain, restore). Updated every tick regardless of perception.
- **`Memory`** — owns the agent's knowledge of the external world. Driven by perception. Returns best targets on request, optionally weighted by urgency.
- **`Agent`** — orchestrates both. Runs the consideration matrix, selects actions, manages navigation.

Each class has a single axis of change: `NeedState` changes when survival mechanics change; `Memory` changes when the knowledge model changes; `Agent` changes when decision logic changes.

```python
urgencies = self.needs.urgency_vector(tick, is_night)
action = self.choose_action(urgencies, candidates, tick)
```

---

## Agent State

Fields are distributed across the three classes by ownership:

**`NeedState`**

| Domain   | Fields                                                             |
| -------- | ------------------------------------------------------------------ |
| Survival | `health` (hunger proxy), `water`, `warmth`, `rest`, `is_sleeping` |
| Traits   | `vision_range`, `metabolism`, `rest_threshold`, `night_drain`      |

**`Memory`**

| Domain | Fields                                                |
| ------ | ----------------------------------------------------- |
| Memory | `food_memories`, `water_memories`, `shelter_memories` |

**`Agent`**

| Domain    | Fields                                                                         |
| --------- | ------------------------------------------------------------------------------ |
| Genetics  | `genotype` (Mendelian allele counts per locus), `mutations` (expressed traits) |
| Navigation | `direction`, `active_task`, `path`, `target`, `last_decision_tick`            |
| Social    | `group_id`, `home_pos`                                                         |
| Inventory | `carried_food` (single item)                                                   |

- **Thirst:** a `water` level that drains over time, satiated by visiting river tiles
- **Warmth:** drains at night, faster on exposed tiles, recovers in shelter; drives shelter-seeking behavior
- **Need urgency model:** a numeric urgency score per need, computed dynamically and used to weight task selection
- **Curiosity:** an inverse-composite drive that fills the headroom when all other needs are low
- **Safety:** group proximity as a passive safety contribution; danger score from proximity to predator tiles (when predators exist)
- **Typed memory:** sparse per-agent memory entries for food, water, and shelter locations with quality and confidence

---

## NeedState

`NeedState` owns all physiological fields and is responsible for computing the urgency vector the agent's consideration matrix consumes.

### Drain and restore

Every tick, `NeedState` is updated by the simulation before action selection:

```python
needs.tick(is_night, on_exposed_tile, is_sleeping)
```

Each field drains or restores according to its own rules (see urgency curves below). `NeedState` does not know about the world — the simulation passes in the context it needs as parameters.

### Urgency vector

```python
needs.urgency_vector(tick, is_night) -> dict[str, float]
```

Returns one urgency score per need. The agent feeds this directly into the consideration matrix. `NeedState` owns all curve logic; the agent never computes urgency itself.

---

## Decision-Making Architecture

### Utility scoring

Each candidate action gets a score that sums contributions from all active needs:

```
score(action) = Σ urgency(need) × relevance(action, need)
```

### The Consideration Matrix

`relevance[action][need]` — values can be negative (fleeing costs reproduction opportunity).

|                  | seek_food | drink | sleep | seek_shelter | find_shelter | flee | mate | explore |
| ---------------- | --------- | ----- | ----- | ------------ | ------------ | ---- | ---- | ------- |
| **hunger**       | 1.0       | 0.0   | 0.1   | 0.0          | 0.0          | 0.0  | 0.0  | 0.2     |
| **thirst**       | 0.0       | 1.0   | 0.1   | 0.0          | 0.0          | 0.0  | 0.0  | 0.2     |
| **rest**         | 0.0       | 0.0   | 1.0   | 0.5          | 0.2          | 0.0  | 0.0  | -0.3    |
| **warmth**       | 0.0       | 0.0   | 0.3   | 1.0          | 0.8          | 0.0  | 0.0  | -0.3    |
| **safety**       | 0.0       | 0.0   | 0.0   | 0.3          | 0.1          | 1.0  | -0.5 | -0.5    |
| **social**       | 0.1       | 0.0   | 0.0   | 0.2          | 0.0          | 0.3  | 0.2  | -0.2    |
| **reproduction** | 0.0       | 0.0   | 0.0   | 0.0          | 0.0          | -0.2 | 1.0  | 0.1     |
| **curiosity**    | 0.0       | 0.0   | 0.0   | 0.0          | 0.1          | 0.0  | 0.0  | 1.0     |

### Need Urgency Curves

Not all needs should be linear. The curve controls _when_ an agent starts caring.

| Need         | Curve                  | Rationale                                                                     |
| ------------ | ---------------------- | ----------------------------------------------------------------------------- |
| hunger       | exponential (`value²`) | agents forage before they're critical                                         |
| thirst       | exponential            | slightly faster drain than hunger                                             |
| rest         | logistic               | ignores mild tiredness, crashes hard when exhausted                           |
| warmth       | logistic + time-gated  | only active after dusk; sharp drop in open tiles at night                     |
| safety       | step function          | threat response is immediate and total                                        |
| reproduction | linear, gated          | only active above a minimum health floor                                      |
| curiosity    | inverse composite      | `max(0, 1 − max_other_urgency × 2)` — fills headroom when other needs are low |

### Curiosity

Curiosity is not scripted as a mode. It emerges from the urgency vector:

```python
def curiosity_urgency(agent):
    max_other = max(hunger_urgency, thirst_urgency, rest_urgency, warmth_urgency)
    return max(0.0, 1.0 - max_other * 2.0)
```

When all needs are low, curiosity dominates and drives exploration. When any real need becomes pressing, curiosity collapses to zero. The agent's "mood" is a consequence of the urgency shape, not a separate state.

### Opportunistic Actions

Some actions are **triggered**, not goal-directed. They fire regardless of the current goal when conditions are met, costing no movement turn:

```python
# Each tick, before goal-directed action selection:
if food_at_current_tile(agent) and agent.hunger > 0.2:
    eat()

if river_adjacent(agent) and agent.thirst > 0.15:
    drink()
```

This is mechanically separate from `seek_food` or `seek_water`, which cost movement. Opportunistic thresholds are intentionally low

### Action Candidacy

Before scoring, filter to feasible actions. Infeasible actions are excluded entirely

| Action         | Requires                                                                     |
| -------------- | ---------------------------------------------------------------------------- |
| `seek_food`    | food not at current tile                                                     |
| `drink`        | river not adjacent                                                           |
| `sleep`        | at home tile or safe tile                                                    |
| `seek_shelter` | warmth urgency > threshold AND shelter memory exists                         |
| `find_shelter` | warmth urgency > threshold AND no shelter memory → explore with shelter bias |
| `flee`         | predator in vision range (Phase 2+)                                          |
| `mate`         | adjacent full-health partner                                                 |
| `explore`      | always available                                                             |

### Action Inertia

Without inertia, agents oscillate every tick between equally-scored actions. A continuation bonus stabilizes behavior:

```python
CONTINUATION_BONUS = 0.15  # tune this

for action in candidates:
    score = dot(urgencies, relevance[action])
    if action == agent.active_task:
        score += CONTINUATION_BONUS
```

Increasing the bonus makes agents more committed; decreasing it makes them more reactive.

---

## Memory

`Memory` is a per-agent class that owns the agent's knowledge of the external world. There is no shared world map — each agent's `Memory` instance is its own. The agent never accesses `MemoryEntry` objects directly; all knowledge operations go through the `Memory` interface.

### Interface

```python
memory.observe(pos, type, quality, tick)        # write: called when agent perceives a resource
memory.query(type, tick, urgency=0.0)           # read: returns best position, or None
```

`observe` is called by the agent each tick after perception. `query` is called during action selection — when urgency is provided, nearby mediocre sources are weighted higher relative to distant good ones.

### Internal structure

```python
@dataclass
class MemoryEntry:
    pos: tuple[int, int]
    type: str           # "food", "water", "shelter"
    quality: float      # how good was it? (0.0–1.0)
    added_tick: int     # tick when confidence was last reset to 1.0
    visit_count: int
    decay_rate: float = 0.001

def confidence(self, current_tick) -> float:
    return max(0.0, 1.0 - (current_tick - self.added_tick) * self.decay_rate)
```

`Memory` maintains three typed lists internally: `food_memories`, `water_memories`, `shelter_memories`.

### Writing

Any time a resource enters vision range, `observe` upserts an entry. New location: insert. Known location: update quality and reset `added_tick` (restoring confidence).

### Reading

`query` scores all entries of the requested type and returns the position of the best:

```python
best = max(memories, key=lambda m: m.quality * m.confidence(tick))
```

### Fading

Confidence is computed lazily on read — no per-tick iteration. Entries with `confidence < 0.05` are pruned when queried. Memory is capped per type (e.g. 10 food entries max) to prevent unbounded growth; lowest-scoring entry is evicted on overflow.

### Emergent behavior

Better resources are revisited more often, keeping their confidence high, which keeps them at the top of the ranked list. Mediocre locations fade out because the agent stops returning to them. The "better resources remembered better" behavior emerges from the structure without any special logic.

---

## Shelter and Temperature

### World side

Every tile has a `wind_exposure` value (0.0 = fully sheltered, 1.0 = fully exposed). Temperature drops at night. An agent's warmth drains faster on exposed tiles.

### Agent side

The agent does not read `wind_exposure` directly. It learns shelter quality from outcomes:

```python
# When agent wakes from sleep at position P:
warmth_recovery_rate = (agent.warmth_now - agent.warmth_when_slept) / ticks_slept
upsert_memory(pos=P, type="shelter", quality=warmth_recovery_rate)
```

On first night: no shelter memory → agent picks the nearest low-urgency position → probably suboptimal → learns a low-quality entry. On subsequent nights: navigates to highest-scoring shelter memory. Over time the list improves as it tries new places and updates quality estimates.

This is outcome-based learning without ML — the agent records what happened and acts on it.

---

## Performance

The utility matrix evaluation is cheap (a few dot products per agent). The expensive operations are perception, pathfinding, and memory.

### Decision throttling

The optimal action almost never changes tick-to-tick. Re-evaluate only when something meaningful changes:

```python
def should_recompute(agent, tick):
    if agent.active_task is None:           return True  # task completed
    if any_urgency_crossed_threshold(agent): return True  # emergency
    if tick - agent.last_decision_tick >= DECISION_INTERVAL: return True
    return False
```

With `DECISION_INTERVAL = 5–10`, ~90% of agents skip full recomputation most ticks.

### Agent staggering

Divide agents into buckets so full decisions are spread across ticks:

```python
if agent.id % DECISION_INTERVAL == tick % DECISION_INTERVAL:
    recompute_action(agent)
```

### Spatial indexing for perception

Instead of each agent scanning ~1,257 tiles per tick (range 20), maintain a spatial hash of resource locations keyed by cell. Vision check becomes a lookup of ~9 nearby cells returning only present resources.

### Path caching

Compute A\* once, follow the cached path step by step. Recompute only when the target moves/disappears or a tile becomes occupied. Most agents following a stable target (known food location, home) use the same path for its full length.

### Lazy memory decay

Confidence is computed on read from `added_tick`, not decremented each tick. Zero per-tick iteration cost regardless of memory size.

### Scaling reference

| Agents | Naive (every tick)   | With optimizations |
| ------ | -------------------- | ------------------ |
| 20     | fine                 | fine               |
| 200    | sluggish             | fine               |
| 1000   | unworkable in Python | manageable         |

**Implementation order:** path caching → spatial index (when vision scans feel slow) → decision throttling (past ~100 agents) → lazy memory decay (when memory entries grow large).
