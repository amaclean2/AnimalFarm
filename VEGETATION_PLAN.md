# Vegetation System — Implementation Plan

Transforms the current food model (ephemeral dots that spawn/despawn) into a persistent plant ecosystem
shaped by climate. Three sequential steps: climate maps, plant types, then harvest mechanics.

---

## Step 1 — Climate Maps ✓ COMPLETED

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

| File              | Change                                                                                                                       |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `world.py`        | Add `_temperature: list[float]` and `_precipitation: list[float]` fields; add `generate_climate(seed)` called from `reset()` |
| `config.py`       | `CLIMATE_COARSE_SCALE = 50.0`, `CLIMATE_MEDIUM_SCALE = 20.0`, `TEMP_ELEVATION_COUPLING = 0.4`                                |
| `routers/game.py` | Include climate arrays in world init payload sent to the client                                                              |
| `renderer.js`     | Optional debug overlay toggled by a key — tints tiles blue (precip) or red (temp)                                            |

---

## Step 2 — Plant Types

Replace the `Food` model with a persistent `Plant` model. A new `VegetationManager` class (in
`plant.py`) owns all plant state and is independent of `World`, exactly as `FoodManager` is today.
`World` has no plant methods — it only provides climate data via `get_climate_at`.

### ClimateData

A lightweight dataclass that bundles all climate variables for a tile. Used by `VegetationManager`
during placement and by agents when evaluating tile desirability.

```python
@dataclass
class ClimateData:
    temperature: float      # 0.0–1.0
    precipitation: float    # 0.0–1.0
    elevation: float        # 0.0–1.0
    river_proximity: float  # 1.0 / (1 + manhattan_dist_to_nearest_river)
```

`world.get_climate_at(x, y) -> ClimateData` is the single compound accessor — the only world
interface `VegetationManager` needs.

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

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)
```

`growth_rate` is baked in at placement time:
`growth_rate = base_growth_rate * suitability(climate)`

where `suitability` returns 0.0–1.0 based on how closely the tile matches the plant's ideal range.

### VegetationManager (`plant.py`)

Mirrors `FoodManager` in structure: instantiated with a `world` reference, owned by `Simulation`
as `self.vegetation`, called directly from the simulation loop.

```python
class VegetationManager:
    def __init__(self, world: World) -> None: ...

    def place_plants(self, seed: int) -> list[Plant]:
        # scores every non-river tile via world.get_climate_at()
        # places the highest-scoring plant type per tile up to PLANT_DENSITY
        # called once from routers/game.py during world init
        ...

    def grow_plants(self, tick: int, events: list[tuple[str, dict]]) -> None:
        # called each tick from simulation.py
        # increments fruit_count up to max_fruit for all plants
        # emits fruit_grew events in batches
        ...

    def get_plant_at(self, pos: Pos) -> Plant | None: ...
    def get_plant(self, plant_id: UUID) -> Plant | None: ...
    def consume_fruit_at(self, pos: Pos) -> Plant | None: ...
    def plants_in_vision(self, agent, vision_range: float | None = None) -> list[Plant]: ...
    def compute_plant_visibility(self, agent_vision: dict, agents) -> dict: ...

    @property
    def all_plants(self) -> list[Plant]: ...

    def reset(self) -> None: ...
```

### Plant Types

| Name                | Temp range | Precip range | River proximity | max_fruit | base_growth_rate | Notes                                                       |
| ------------------- | ---------- | ------------ | --------------- | --------- | ---------------- | ----------------------------------------------------------- |
| **Xerophyte**       | 0.65–1.0   | 0.0–0.25     | none            | 5         | 0.008            | Hot, dry. Sparse fruit but thrives where nothing else can.  |
| **Riparian Reed**   | 0.2–0.9    | any          | ≤ 6 tiles       | 20        | 0.06             | Must be adjacent to river. High yield, wide temp tolerance. |
| **Rainforest Vine** | 0.55–1.0   | 0.60–1.0     | none            | 14        | 0.04             | Warm and wet anywhere. Dense clusters in jungle zones.      |
| **Temperate Berry** | 0.30–0.70  | 0.30–0.65    | none            | 10        | 0.03             | Mild climate generalist. Most common plant overall.         |
| **Boreal Shrub**    | 0.0–0.40   | 0.20–0.60    | none            | 8         | 0.02             | Cold uplands and highlands. Survives where vines cannot.    |

Suitability falls off linearly outside the stated ranges, reaching 0.0 at ±0.15 beyond each edge.
A plant with suitability below a minimum threshold (e.g. 0.1) is not placed at that tile.

### Placement (replaces cluster seeding)

Called once from `routers/game.py` after world generation: `vegetation.place_plants(seed)`.
Scoring uses `world.get_climate_at(x, y)` for each candidate tile — no other world coupling needed.
Total plant count is controlled by a target density constant rather than `NUM_FOOD_CLUSTERS`.

```
PLANT_DENSITY = 0.06   # fraction of non-river tiles that become plants
```

This replaces `NUM_FOOD_CLUSTERS`, `CLUSTER_SIGMA`, `FOOD_SPREAD_SIGMA`, `FOOD_SPREAD_CANDIDATES`.

### Regrowth (replaces spawn_food_near)

`simulation.py` calls `self.vegetation.grow_plants(tick, events)` each tick directly — no
intermediary. `VegetationManager` handles all regrowth logic internally.

```python
for plant in self._plants.values():
    plant.fruit_count = min(plant.max_fruit, plant.fruit_count + plant.growth_rate)
```

Plants that drop to `fruit_count = 0` remain visible — they are bare, not gone.

### Changes

| File              | Change                                                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `food.py`         | Delete                                                                                                                                            |
| `ecology.py`      | Delete                                                                                                                                            |
| `plant.py`        | New file — `Plant` model + `VegetationManager` class                                                                                              |
| `world.py`        | Add `get_climate_at(x, y) -> ClimateData`; `_river_extend` no longer takes `food` param — removes drowned-food event or handles it via vegetation |
| `simulation.py`   | `self.food` → `self.vegetation: VegetationManager`; add `self.vegetation.grow_plants(tick, events)` to the tick loop                              |
| `routers/game.py` | World init: call `vegetation.place_plants(seed)` after world generation                                                                           |
| `config.py`       | Add per-type constants (ranges, max_fruit, base_growth_rate), `PLANT_DENSITY`; remove food spread constants                                       |
| `renderer.js`     | Plants are permanent sprites; fruit count shown as fill level (empty/sparse/full) or color intensity                                              |
| `state.js`        | Maintain `plants` map; update on `fruit_depleted` / `fruit_grew` events rather than `food_ate` / `food_grew`                                      |

### New events

| Event            | Payload                                         |
| ---------------- | ----------------------------------------------- |
| `fruit_depleted` | `plant_id, x, y` — fruit_count hit 0            |
| `fruit_grew`     | `plant_id, fruit_count` — periodic batch update |
| `plant_placed`   | `plant: {...}` — emitted during world init      |

---

## Step 2b — Tile Inspector Panel

When the user clicks a tile with no agent on it, a **tile inspector panel** appears (mirroring the agent panel). Clicking the same empty tile again dismisses it. If the clicked tile has an agent, the agent panel takes priority and the tile panel is hidden.

### Data shown

| Field             | Source                                                     |
| ----------------- | ---------------------------------------------------------- |
| Tile coordinates  | computed from click                                        |
| Tile type         | `rivers` set → plant type name → `"Bare"`                  |
| Elevation         | `ClimateData.elevation` — via `world.get_climate_at(x, y)` |
| Temperature       | `ClimateData.temperature`                                  |
| Precipitation     | `ClimateData.precipitation`                                |
| Plant type name   | `plant.plant_type`                                         |
| Fruit count / max | `plant.fruit_count / plant.max_fruit`                      |
| Growth rate       | `plant.growth_rate`                                        |

Tile type resolves in priority order: **river → plant type name → bare ground**.

### Display format

Values in the `0.0–1.0` range are shown as bar fills matching the agent panel bars:

- **Elevation** — grey bar
- **Temperature** — red-tinted bar
- **Precipitation** — blue-tinted bar
- **Fruit** — green bar with `{current}/{max}` label

Panel header shows `Tile (x, y)` and the resolved type label (e.g. `River`, `Temperate Berry`, `Bare`).

### Changes

| File         | Change                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `state.js`   | Add `selectedTile: {x, y} \| null`; export `getSelectedTile` / `setSelectedTile`                                                                                               |
| `main.js`    | `handleCanvasSelect`: if no agent hit, call `setSelectedTile({x, y})` and `updateTilePanel(worldX, worldY)`; if agent hit, call `setSelectedTile(null)` to clear tile panel    |
| `ui.js`      | Add `updateTilePanel(x, y)` — reads climate from `ClimateData` payload and plant state; renders into `#tile-panel`; add `clearTilePanel()` called on agent select or sim reset |
| `index.html` | Add `#tile-panel` element with same structure as `#agent-panel`                                                                                                                |

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

| Plant       | harvest_cost (ticks) | Rationale                        |
| ----------- | -------------------- | -------------------------------- |
| Date Palm   | 6                    | Tough exterior, sparse payoff    |
| Wild Plum   | 2                    | Accessible, abundant             |
| Fig Tree    | 4                    | Climbing and reaching required   |
| Berry Bush  | 3                    | Standard foraging                |
| Bilberry    | 5                    | Frozen ground, harder extraction |

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
    "date_palm": 6,
    "wild_plum": 2,
    "fig_tree": 4,
    "berry_bush": 3,
    "bilberry": 5,
}
HARVEST_CONTINUATION_BONUS = 0.25
```

### Changes

| File                | Change                                                                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent/__init__.py` | Add `harvest_target`, `harvest_ticks` fields                                                                                                        |
| `agent/needs.py`    | Urgency scorer respects `harvest_target`; harvest continuation bonus                                                                                |
| `simulation.py`     | Eat action becomes multi-tick: increment ticks, check threshold, call `self.vegetation.consume_fruit_at(pos)` on completion; emit `fruit_harvested` |
| `config.py`         | `HARVEST_COST` dict, `HARVEST_CONTINUATION_BONUS`                                                                                                   |
| `renderer.js`       | Show harvesting agents with a subtle work animation or progress indicator                                                                           |

### New events

| Event               | Payload                                     |
| ------------------- | ------------------------------------------- |
| `harvest_started`   | `agent_id, plant_id`                        |
| `harvest_abandoned` | `agent_id, plant_id, ticks_lost`            |
| `fruit_harvested`   | `agent_id, plant_id, fruit_count_remaining` |
