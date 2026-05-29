# Vegetation System — Implementation Plan

Transforms the current food model (ephemeral dots that spawn/despawn) into a persistent plant ecosystem
shaped by climate. Three sequential steps: climate maps, plant types, then harvest mechanics.

---

## Step 1 — Climate Maps

Add two new world-wide scalar fields: **temperature** and **precipitation**. These are generated once
at world creation alongside elevation and remain static per seed (seasonal modulation can come later).

### Generation

Both fields use the existing `_value_noise_2d` in `world.py`, but with very coarse scale (~50 tiles)
so gradients are continental rather than local. A small amount of medium noise (~20 tiles) adds texture.

**Temperature** is blended with elevation — higher ground is colder:

```
raw_temp  = 0.8 * noise(scale=50) + 0.2 * noise(scale=20)
temperature[x, y] = raw_temp * (1 - 0.4 * elevation[x, y])
```

**Precipitation** is independent noise on a different seed axis:

```
precipitation[x, y] = 0.75 * noise(scale=50) + 0.25 * noise(scale=20)
```

Both values are clamped to `[0.0, 1.0]`.

### Changes

| File | Change |
|---|---|
| `world.py` | Add `_temperature: list[float]` and `_precipitation: list[float]` fields; add `generate_climate(seed)`, `temperature_at(x, y)`, `precipitation_at(x, y)` methods; call from `reset()` |
| `config.py` | `CLIMATE_COARSE_SCALE = 50.0`, `CLIMATE_MEDIUM_SCALE = 20.0`, `TEMP_ELEVATION_COUPLING = 0.4` |
| `routers/game.py` | Include climate arrays in world init payload sent to the client |
| `renderer.js` | Optional debug overlay toggled by a key — tints tiles blue (precip) or red (temp) |

### What it enables

Every tile now has a `(temperature, precipitation, river_proximity)` triple. This is the input
that plant suitability scoring reads from in Step 2.

---

## Step 2 — Plant Types

Replace the `Food` model with a persistent `Plant` model. Plants are placed once at world generation
based on climate suitability and remain on the map permanently. Instead of disappearing when eaten,
they carry a `fruit_count` that depletes and regrows over time.

### Plant Model (`plant.py`)

```python
class Plant(BaseModel):
    id: UUID
    x: int
    y: int
    plant_type: str          # see table below
    fruit_count: int         # current harvestable fruit (0 → max_fruit)
    max_fruit: int           # determined by type
    growth_rate: float       # fruit per tick, scaled by local climate fitness
```

`growth_rate` is baked in at placement time:
`growth_rate = base_growth_rate * suitability(temp, precip, river_dist)`

where `suitability` returns 0.0–1.0 based on how closely the tile matches the plant's ideal range.

### Plant Types

| Name | Temp range | Precip range | River proximity | max_fruit | base_growth_rate | Notes |
|---|---|---|---|---|---|---|
| **Xerophyte** | 0.65–1.0 | 0.0–0.25 | none | 5 | 0.008 | Hot, dry. Sparse fruit but thrives where nothing else can. |
| **Riparian Reed** | 0.2–0.9 | any | ≤ 6 tiles | 20 | 0.06 | Must be adjacent to river. High yield, wide temp tolerance. |
| **Rainforest Vine** | 0.55–1.0 | 0.60–1.0 | none | 14 | 0.04 | Warm and wet anywhere. Dense clusters in jungle zones. |
| **Temperate Berry** | 0.30–0.70 | 0.30–0.65 | none | 10 | 0.03 | Mild climate generalist. Most common plant overall. |
| **Boreal Shrub** | 0.0–0.40 | 0.20–0.60 | none | 8 | 0.02 | Cold uplands and highlands. Survives where vines cannot. |

Suitability falls off linearly outside the stated ranges, reaching 0.0 at ±0.15 beyond each edge.
A plant with suitability below a minimum threshold (e.g. 0.1) is not placed at that tile.

### Placement (replaces cluster seeding)

At world gen, candidate tiles are scored for each plant type based on suitability. The highest-scoring
plant type wins each tile; ties broken randomly. Total plant count is controlled by a target density
constant rather than `NUM_FOOD_CLUSTERS`.

```
PLANT_DENSITY = 0.06   # fraction of non-river tiles that become plants
```

This replaces `NUM_FOOD_CLUSTERS`, `CLUSTER_SIGMA`, `FOOD_SPREAD_SIGMA`, `FOOD_SPREAD_CANDIDATES`.

### Regrowth (replaces spawn_food_near)

Each tick, the ecology loop calls `grow_plants(world)`:

```python
for plant in world.all_plants():
    plant.fruit_count = min(plant.max_fruit, plant.fruit_count + plant.growth_rate)
```

`spawn_food_near` is removed. Plants that drop to `fruit_count = 0` are still visible — they are
bare, not gone.

### Changes

| File | Change |
|---|---|
| `food.py` | Delete |
| `plant.py` | New file — `Plant` model |
| `world.py` | `_food` → `_plants: dict[tuple, Plant]`; all food methods renamed/replaced; add `place_plant`, `get_plant_at`, `all_plants`, `consume_fruit_at` |
| `ecology.py` | Remove `spawn_food_near`; add `grow_plants`; placement logic moved to `routers/game.py` world init |
| `routers/game.py` | World init: score + place plants using climate data |
| `config.py` | Add per-type constants (ranges, max_fruit, base_growth_rate), `PLANT_DENSITY`; remove food spread constants |
| `renderer.js` | Plants are permanent sprites; fruit count shown as fill level (empty/sparse/full) or color intensity |
| `state.js` | Maintain `plants` map; update on `fruit_depleted` / `fruit_grew` events rather than `food_ate` / `food_grew` |

### New events

| Event | Payload |
|---|---|
| `fruit_depleted` | `plant_id, x, y` — fruit_count hit 0 |
| `fruit_grew` | `plant_id, fruit_count` — periodic batch update |
| `plant_placed` | `plant: {...}` — emitted during world init |

---

## Step 3 — Harvest Energy

Eating is no longer instant. An agent must spend multiple ticks working at a plant tile to extract
fruit. This models the real cost of foraging — climbing a tree, stripping a bush, digging a root.

### Harvest mechanic

When an agent arrives at a plant tile with fruit, it enters a **harvesting** state. Each tick spent
at the tile increments `agent.harvest_ticks`. When `harvest_ticks` reaches the plant's
`harvest_cost`, the agent receives `EAT_RESTORE` hunger and `fruit_count` decrements by 1.
`harvest_ticks` resets to 0 and the agent can harvest again immediately if fruit remains and hunger
warrants it.

The agent aborts harvesting if:
- hunger drops below `SLEEP_HUNGER_OVERRIDE` and rest is more urgent
- a higher-priority need fires (critical thirst, extreme cold)
- the plant runs out of fruit mid-harvest (ticks are lost, agent must move)

### Harvest costs by plant type

| Plant | harvest_cost (ticks) | Rationale |
|---|---|---|
| Xerophyte | 6 | Tough exterior, sparse payoff |
| Riparian Reed | 2 | Accessible, abundant |
| Rainforest Vine | 4 | Climbing and reaching required |
| Temperate Berry | 3 | Standard foraging |
| Boreal Shrub | 5 | Frozen ground, harder extraction |

### Agent state changes

```python
# new fields on Agent
harvest_target: UUID | None = None   # plant being worked
harvest_ticks: int = 0               # progress toward harvest_cost
```

On any movement tick (agent walks away, is displaced, or changes decision), both fields reset.

### Decision loop changes

The `needs.py` urgency scorer gains a `HARVEST_CONTINUATION_BONUS` stacked on top of the existing
`CONTINUATION_BONUS` when `agent.harvest_target` is set and the plant still has fruit. This prevents
agents from abandoning a half-finished harvest for a marginally better option one tile away.

```python
HARVEST_COST = {
    "xerophyte": 6,
    "riparian_reed": 2,
    "rainforest_vine": 4,
    "temperate_berry": 3,
    "boreal_shrub": 5,
}
HARVEST_CONTINUATION_BONUS = 0.25
```

### Changes

| File | Change |
|---|---|
| `agent/__init__.py` | Add `harvest_target`, `harvest_ticks` fields |
| `agent/needs.py` | Urgency scorer respects `harvest_target`; harvest continuation bonus |
| `simulation.py` | Eat action becomes multi-tick: increment ticks, check threshold, emit `fruit_harvested` on completion |
| `config.py` | `HARVEST_COST` dict, `HARVEST_CONTINUATION_BONUS` |
| `renderer.js` | Show harvesting agents with a subtle work animation or progress indicator |

### New events

| Event | Payload |
|---|---|
| `harvest_started` | `agent_id, plant_id` |
| `harvest_abandoned` | `agent_id, plant_id, ticks_lost` |
| `fruit_harvested` | `agent_id, plant_id, fruit_count_remaining` |

---

## Summary of removed constants

These constants in `config.py` become obsolete and should be deleted:

- `NUM_FOOD_CLUSTERS`
- `CLUSTER_SIGMA`
- `FOOD_SPREAD_SIGMA`
- `FOOD_SPREAD_CANDIDATES`
- `FOOD_WATER_WEIGHT`
- `FOOD_CLUSTER_WEIGHT`
- `FOOD_SCORE_FLOOR`
- `FOOD_REGROW_TICKS`
- `FOOD_PEAK_PROBABILITY`
