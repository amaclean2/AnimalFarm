VisionSnapshot: an object of everything the agent sees
I don't know what visible_q is

> `visible_q` is the rest quality score of the nearest suitable rest tile in vision (computed at line 220–221). Rename to `visible_rest_quality`.

Shouldn't this be a part of agent?

> No — it's assembled by Simulation from world/vegetation data the agent doesn't own. It's a transient per-tick input to planning, not agent state. Putting it on Agent would couple the agent to those systems.

Simulation: The app main accumulator
world: the app geography
vegetation: everything an agent can eat, made up of plant objects
agents: a class containing the group of agents
genome_pool: all the agent traits

- shouldn't this also be a part of agents?
  > No — genome_pool is a cross-simulation archive that records across multiple `_sim_id` runs. Agents is a single-sim registry. They have different lifecycles, so keeping them separate is correct.

self.\_sim_id: I don't know what this is for

> It tags genome records with which simulation run produced them (line 431: `self._genome_pool.record(agent, self._sim_id, tick_count)`), so you can distinguish lineages across resets.

what are candidates?

> Valid adjacent move positions that aren't already occupied by another agent (lines 248–249).

Rename to valid moves?

occupied should be renamed to occupied_tiles

> Agreed.

why does tick_count need to be passed into \_plan_steps? Can't it be a global variable to the class?

> It's threaded into `find_mate_target`, `explore_goal`, `thirst_explore_goal` — all time-dependent. Passing it explicitly keeps those functions pure and testable. Making it a class variable would work but requires discipline about when it's updated.

Keeping self.tick_count would clean up function definitions a lot. It can still be passed to the relevant agent methods, and can be set in self.on_tick.

why is rest_target not a part of snapshot?

> `rest_target` is persistent agent state that survives across ticks, not a fresh observation. VisionSnapshot holds transient per-tick observations. The separation is intentional.

I think I want to abandon the concept of keeping a memory of rest spots now. It's adding complexity that isn't important to the simulation

understand lines 60-66

> This is the planning entry point. It assembles all possible goal positions (mate, explore, water, food) and picks the highest-priority Task via `agent.choose_action`.

what does effective_food mean?
I guess it means food targets, but why are the targets dependent on the agent task state, the targets should be there regardless.

> When the agent's top need is thirst (`thirst_explore` or `seek_water`), food targets are zeroed out so `best_move` doesn't pull the agent toward food instead of water. The name is cryptic — `pathfinding_food_targets` would be clearer.

Why can't we just compute food targets once we've decided seek_food is the top priority?

line 79: is there a way to collect targets in an order of closest to furthest, like checking tiles from the agent spiraling outward? That way this sort doesn't have to be computed per agent, per tick

> This is `min()` not a sort — it's a single O(n) linear scan, not O(n log n). For current agent counts this is fine. A spiral/BFS would let you short-circuit on first hit, but the added complexity may not be worth it unless profiling shows a bottleneck here.

Same with line 90.

> Same answer — `min()` linear scan, not a sort.

Should should_replan be calculated in simulation.py or in Agent?

> Either is reasonable. It only uses agent state (`active_task`, `path`) plus `top_task` which is computed locally. It could move to Agent as `needs_replan(top_task)` but that requires passing `top_task` in. Current location isn't wrong.

I want to make an effort to clean up unnecessary logic out of simulation.py, so I'd like to move this.

On line 148, len(steps) is only ever 1 here and cfg.PLAN_HORIZON is 2 making this conditional redundant

> Correct. `steps = [first_step]` always has exactly 1 element, so `len(steps) < cfg.PLAN_HORIZON` is always True. Remove the condition.

On line 159, why would harvest_yield be less than 0?

> Defensive guard. `harvest_yield` is set by `begin_harvest` and could be 0 if the plant loses fruit between harvest start and delivery. The `<= 0` check handles that edge case.

This is over-guarding.

On line 162, plant should be renamed to local_plant

> Agreed.

On line 164, the plant isn't consuming anything. It should be plant.remove

> Agreed — rename `Plant.consume` to `Plant.remove`. "consume" implies the agent is eating it; the plant's method is just decrementing fruit count.

Also, I changed my mind. I want the agent to harvest one fruit at a time rather than have a harvest_count

> Got it — remove `harvest_count`/`harvest_yield` batching, harvest exactly 1 fruit per harvest tick. This simplifies `_do_harvest_tick` considerably.

Not necessarily 1 fruit per tick, since one fruit could take multiple ticks, but don't batch-harvest fruit.

On line 187 shouldn't this be plant.fruit_count == 0?

> Agreed. `fruit_count` is an integer and `consume` clamps to 0, so `== 0` is correct and more precise.

On line 195, the return statement, the plant would never have been none, correct? Why would this ever be False?

> Correct — if `harvest_yield > 0` and we reach line 195, we already passed the `if plant:` guard at line 163, so `plant` cannot be None here. The line can just be `return True`.

On line 211, close should be close_plants

> Agreed.

Again, 211, vegetation isn't a property on world, right? Vegetation should be just self.vegetation.

> Correct — `vegetation` is not on `World` at all (confirmed). This is a bug. Should be `self.vegetation`.

On line 218, why is visible_rest calculated only when the agent might need rest, but visible_water is calculated regardless?

> Intentional asymmetry: `suitable_rest_in_vision` is more expensive, so it's gated on need. `tiles_near` for water is a cheap range query. Could apply the same gating to water but it's not incorrect as-is.

I want to keep all of them gated for code consistency.

If tick needs increments needs, then it should be called increment_needs on line 260

> Agreed — rename `tick_needs` to `increment_needs`.

Why is tick_count passed through function dependencies rather than being a class variable?

> Same answer as above — passing it explicitly keeps functions pure and testable. A class variable would require discipline about update timing.

Because there's so much shared logic between different parts of the app, I want to keep as much state global as possible and not have to pass it through children. If there's such thing as like a redux state manager, that might be an interesting thing to think about implementing.

On line 286, it's fine because it's being passed from simulation to agent

> Correct.

Line 292: why does next_decision_tick need to be labeled?

> Because it's also set on line 313 (pre-emption on harvest start) and line 325 (after planning). It needs to be settable from outside Agent. The name `next_decision_tick` is more self-documenting than a bare counter.

I'm still not sure I understand.

Line 369: wouldn't it make more semantic sense for agent.tick_movement to return the new position? Or if the new position is saved as agent.pos, wouldn't it make sense to create an old_pos = agent.pos reference before calling agent.tick_movement, and tick_movement would return nothing?

> `tick_movement` already returns `old_pos` (which is what line 369 captures). Your alternative — `old_pos = agent.pos` before the call, then `tick_movement` returns nothing — is equally clean. Either works; pick the one that reads more clearly.

I like setting the reference first then returning nothing.

Line 378: Shouldn't the elevation_drain be applied in the same step as agent.tick_movement?

> Agreed — `drain_uphill` is a direct consequence of movement and should live inside `tick_movement` rather than being applied separately after it.

Line 442: When agent_vision is calculated, would it be too expensive to add this to the individual agent? I don't understand why this is a separate dictionary from agents

> `agent_vision` is just `{a.id: float(a.vision_range) for a in all_living}` — it computes nothing the agent doesn't already know. You could replace every `agent_vision[agent.id]` with `float(agent.vision_range)` and remove the dict. It exists as a convenience for passing into `compute_plant_visibility`.

I want to make this update.

Line 443: Then this object would live on agents, too

> Correct — if you put vision directly on the agent, `compute_plant_visibility`'s signature cleans up and the dict goes away.

Line 446: Why is sleeping_tiles a different set than occupied

> `occupied` = all agent positions (blocks movement). `sleeping_tiles` = only sleeping agent positions (used in `suitable_rest_in_vision` to avoid placing a rest target where someone is already sleeping). Different semantic purposes.

Line 448: What does build_spatial_grid() do?

> It buckets agents into a coarse grid (bucket size 5) so `in_range` can do fast bucket lookups instead of scanning all agents. Used by `find_mate_target`. See agents/**init**.py lines 56–62.

Line 454: Why is reproduce not Agents.reproduce?

> It's a free function imported from `agents.reproduction`. Moving it to `Agents` would be cleaner — it uses both `agents` and `world` as arguments, which is a sign it belongs on one of them.
