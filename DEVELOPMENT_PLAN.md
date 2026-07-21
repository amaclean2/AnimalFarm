# AnimalFarm Development Plan

## Core model

- Every action scores itself on expected survival, using `get_ticks_to_empty`, and the agent dies once a need hits zero. Each tick the agent takes whichever action scored highest. Most of the machinery for this already exists in `calculate_urgencies` `scored_tasks` and `breakaway_margin`. Fitness itself is tracked separately as lifespan multiplied by offspring.
- Capabilities are new actions. Each one ships as its own scorer plus a gene or two, and the selector logic never has to change to accommodate them.
- Constraints are environmental pressures that shift the inputs going into existing scorers, rather than adding new decision branches. A storm raising rest drain is enough on its own to make shelter outscore foraging, no special-casing required.
- There's no hand tuning. Scorer weights are genes, so the right response to a new pressure gets found by selection rather than written in by hand.

### Utility Refactor

Before any of that works, the `choose_action` cascade's early, special-cased returns need to move into the scoring layer, so every action is actually competing on the same currency. It's a one-time cost, but a necessary one. Once it's paid, every later phase just adds a scorer and a gene or two.

## Ongoing

- Forage reliability is the metric to watch, since the whole plan hinges on population growth outpacing food and creating real scarcity. Instrument it early. Nothing downstream matters until scarcity actually bites.
- Lineage (`parent_ids`) is cheap to add now and pays off later. It makes every later phase analyzable and opens the door to kin effects.
- Track gene, skill, and cooperation-rate trends in `routers/stats.py`, and surface them on the frontend.

## Trajectory

Ordered so each pressure shows up right before the capability that answers it.

1. Skill and practice. Skill is just a rep count, valued on log_2(x) so early reps matter more than later ones. Skill scales performance on every task.
2. Harvest efficiency. Swap `ticks_per_fruit` for `fruit_per_tick`, scaled by skill on that same log curve, so there's no ceiling on how efficient an agent can get, just diminishing returns. Agents can only ever collect whole fruit, so harvesting has to run long enough for `fruit_per_tick` times ticks to clear one. Whatever's collected when the agent stops harvesting gets kept. Any partial progress toward the next fruit is lost.
3. Population pressure into scarcity. More efficient harvesting means more offspring, which means more agents competing over the same fixed plant economy. Tune regrowth and density until local depletion actually bites. This is the pivot the rest of the plan is built around.
4. Carry and inventory. Agents get a carrying capacity, hold onto what they gather until the task ends, and eat from inventory. Water still gets consumed immediately, until vessels exist. Once scarcity sets in, carrying food in batches beats making a separate trip every time an agent gets hungry.
5. Caching, or scatter hoarding. Agents can drop surplus on whatever tile they're standing on, no dedicated trip needed. A cache is really just a food-memory entry the agent left behind, picked back up later through the existing `seek_food` behavior. There's no real security to it beyond redundancy, so scattered stores just degrade a little under theft rather than collapsing outright. The propensity to cache is its own gene, worth nothing until scarcity makes it worth something.
6. Weather, storms and floods mainly, destroys caches left out in the open, and raiding on top of that compounds the loss. That's the pressure that pushes agents toward consolidating everything into one defended spot.
7. Shelter, home, and larder. Scattered caches get consolidated into a single defended site. Home quality comes from site quality, construction skill, and materials invested, multiplied together, and that quality is what determines how much shelter cuts into cold and night drain. This is also where a site-quality heuristic earns its place, essentially the round-trip distance to every vital need, reusing the existing rest-quality grid, along with a gene for cache ownership and respect. Materials come from breaking weak plants for sticks; trees need actual tools.
8. Cold and night severity. Turn up the cold and night drain multipliers so shelter quality actually matters for survival instead of just being nice to have.
9. Infant dependency. A dependent infant stays put at a fixed site, and `feed_child` uses the carry mechanic to bring it food. This needs lineage already in place. It's the most direct driver of cooperation in the whole plan, and the first cache trip that's genuinely deliberate rather than opportunistic, driven by the infant's need instead of the parent's convenience.
10. Crafting and tools. Vessels for carrying water, tools for harvesting trees. New skills unlocking new capabilities, which become new scorers in turn.
11. Direct cooperation. Agents get explicit share and assist actions, and the cache-respect and kin-respect genes become the substrate cooperation actually evolves on.
12. Group-aware selection. Feed family and group outcomes into `GenomePool.record`, instead of just individual lifespan times offspring, and chart cooperative-event rates across generations.

## Backlog

- Bounded knowledge: meaningful scouting and learned shortcuts, touching `World`, `Memory`, and `pathfinding` all at once. Worth revisiting once specialization makes map knowledge actually valuable.
- Trading: carry a surplus, find a specific agent to swap with, and let comparative advantage do the rest.
- Defense: a second agent type or threat source, enough to create real pressure for group defense.
