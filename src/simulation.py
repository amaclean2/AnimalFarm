import random
from pathlib import Path

from agents import Agents
from agents.agent import Agent
from clock import DAY_LENGTH
from plant import Plant, VegetationManager
from metrics import SimulationMetrics
from movement import best_move
from pos import Pos
from tasks import Task
from pathfinding import astar
from agents.reproduction import reproduce
import config as cfg
from world import World


class Simulation:
    _PROFILE_START = 700
    _PROFILE_END = 1200

    def __init__(
        self, world: World, vegetation: VegetationManager, agents: Agents
    ) -> None:
        self.world = world
        self.vegetation = vegetation
        self.agents = agents
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged: bool = False
        self._task_counts: dict[str, int] = {}
        self._profile_ticks: int = 0

    def save_log(self) -> None:
        if not self._game_logged and self._metrics._ticks > 0:
            self._metrics.write_game_log()
            self._game_logged = True

    def prepare(self) -> None:
        """Reinitialize metrics with the current runtime config before a new game starts."""
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged = False
        self._task_counts = {}
        self._profile_ticks = 0

    def reset(self) -> None:
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged = False
        self._task_counts = {}
        self._profile_ticks = 0
        self.world.reset()
        self.vegetation.reset()
        self.agents.reset()

    def _plan_steps(
        self,
        agent: Agent,
        candidates: list[Pos],
        food_targets: list[Plant],
        vision: float,
        is_night: bool,
        occupied: set[Pos] | None = None,
        tick_count: int = 0,
        rest_target: Pos | None = None,
        visible_water: list[Pos] | None = None,
    ) -> list[Pos]:
        top_task = agent.choose_action(
            is_night,
            self.agents.find_mate_target(agent, vision, tick_count),
            agent.explore_goal(self.world.width, self.world.height, tick_count),
            agent.thirst_explore_goal(self.world.width, self.world.height, tick_count),
            tick_count,
            rest_target=rest_target,
            harvesting=agent.harvest_target is not None,
        )

        effective_food = [] if top_task.name == "thirst_explore" else food_targets

        if top_task.name == "seek_food" and top_task.goal_pos == agent.pos:
            return [agent.pos]

        if top_task.name == "seek_food" and food_targets:
            nearest = min(
                food_targets,
                key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y),
            )
            top_task = Task(
                priority=top_task.priority,
                name="seek_food",
                goal_pos=nearest.pos,
            )

        if top_task.name == "drink":
            water_candidates = (
                visible_water
                if visible_water is not None
                else [
                    pos
                    for pos in self.world.rivers.all_tiles
                    if abs(pos.x - agent.x) <= int(vision)
                    and abs(pos.y - agent.y) <= int(vision)
                    and abs(pos.x - agent.x) + abs(pos.y - agent.y) <= int(vision)
                ]
            )
            if water_candidates:
                nearest_water = min(
                    water_candidates,
                    key=lambda pos: abs(pos.x - agent.x) + abs(pos.y - agent.y),
                )
                top_task = Task(
                    priority=top_task.priority,
                    name="drink",
                    goal_pos=nearest_water,
                )

        should_replan = (
            agent.active_task is None
            or top_task.name != agent.active_task.name
            or top_task.goal_pos != agent.active_task.goal_pos
            or not agent.path
        )

        if should_replan:
            agent.path = astar(
                self.world, agent.pos, top_task.goal_pos, occupied, int(vision)
            )
            agent.active_task = top_task

        # Determine first step
        first_step: Pos | None = None
        if agent.path:
            step = agent.path[0]
            if step in candidates:
                agent.path.pop(0)
                first_step = step
            else:
                agent.path = astar(
                    self.world, agent.pos, top_task.goal_pos, occupied, int(vision)
                )
                if agent.path and agent.path[0] in candidates:
                    first_step = agent.path.pop(0)
                elif (agent.id.int + tick_count) % 2 == 0:
                    first_step = agent.pos
        elif top_task.name == "sleep":
            first_step = agent.pos

        if first_step is None:
            first_step = best_move(agent, candidates, effective_food)

        steps = [first_step]

        # Peek at the next A* step for the lookahead (don't pop — executed later)
        if first_step != agent.pos and agent.path and len(steps) < cfg.PLAN_HORIZON:
            steps.append(agent.path[0])

        return steps

    def _should_continue_harvesting(self, agent: Agent) -> bool:
        if agent.harvest_target is None:
            return False
        if agent.needs.water < 0.1:
            return False
        plant = self.vegetation.get_plant_at(agent.pos)
        return (
            plant is not None
            and plant.id == agent.harvest_target
            and plant.fruit_count >= 1
        )

    def _tick_harvest(self, agent: Agent, events: list[tuple[str, dict]]) -> bool:
        plant = self.vegetation.get_plant_at(agent.pos)

        if plant is None or plant.fruit_count < 1:
            if agent.harvest_target is not None:
                events.append(
                    (
                        "harvest_abandoned",
                        {
                            "agent_id": str(agent.id),
                            "plant_id": str(agent.harvest_target),
                            "ticks_lost": agent.harvest_ticks,
                        },
                    )
                )
            agent.harvest_target = None
            agent.harvest_ticks = 0
            return False

        if agent.harvest_target != plant.id:
            if agent.harvest_target is not None:
                events.append(
                    (
                        "harvest_abandoned",
                        {
                            "agent_id": str(agent.id),
                            "plant_id": str(agent.harvest_target),
                            "ticks_lost": agent.harvest_ticks,
                        },
                    )
                )
            agent.harvest_target = plant.id
            agent.harvest_ticks = 0
            events.append(
                (
                    "harvest_started",
                    {"agent_id": str(agent.id), "plant_id": str(plant.id)},
                )
            )

        agent.harvest_ticks += 1
        cost = cfg.HARVEST_COST.get(plant.plant_type, 3)

        if agent.harvest_ticks < cost:
            return False

        consumed = self.vegetation.consume_fruit_at(agent.pos)
        if consumed is None:
            return False

        agent.eat()
        agent.harvest_ticks = 0
        events.append(
            (
                "agent_ate",
                {
                    "agent": agent.model_dump(mode="json"),
                    "plant_id": str(consumed.id),
                },
            )
        )
        events.append(
            (
                "fruit_harvested",
                {
                    "agent_id": str(agent.id),
                    "plant_id": str(consumed.id),
                    "fruit_count_remaining": consumed.fruit_count,
                },
            )
        )
        if consumed.fruit_count < 1:
            events.append(
                (
                    "fruit_depleted",
                    {
                        "plant_id": str(consumed.id),
                        "x": consumed.x,
                        "y": consumed.y,
                    },
                )
            )
        return True

    def _decide_agent_step(
        self,
        agent: Agent,
        agent_vision: dict,
        agent_plants: dict,
        occupied: set[Pos],
        sleeping_tiles: set[Pos],
        events: list[tuple[str, dict]],
        tick_count: int,
        is_night: bool,
        profiling: bool,
        tick_task_counts: dict[str, int],
    ) -> bool:
        """Run full decision pipeline for one agent. Returns True if agent should die."""
        moves = self.world.valid_moves(agent.pos)
        if not moves:
            return False

        candidates = [m for m in moves if m not in occupied]
        if not candidates:
            return False

        food_targets = [p for p in agent_plants.get(agent.id, []) if p.fruit_count >= 1]

        if (
            agent.active_task is not None
            and agent.active_task.name == "seek_food"
            and agent.path
        ):
            nearby = [
                p for p in food_targets if abs(p.x - agent.x) + abs(p.y - agent.y) <= 5
            ]
            if nearby:
                food_targets = nearby

        agent.update_food_memory(food_targets, tick_count)

        vision = agent_vision[agent.id]
        vision_int = int(vision)
        ax, ay = agent.x, agent.y
        visible_water = self.world.rivers.tiles_near(ax, ay, vision_int)
        agent.update_water_memory(visible_water, tick_count)

        tile_quality = self.world.rest_quality_at(agent.pos)
        shade = self.vegetation.shade_at(ax, ay)
        temperature = cfg.temp_to_c(
            max(
                0.0,
                self.world.weather.temperature_grid[ay * self.world.width + ax] - shade,
            )
        )
        agent.tick_needs(is_night, tile_quality=tile_quality, temperature=temperature)

        if agent.needs.rest < 0.8:
            visible_rest = self.world.best_rest_in_vision(agent, 10, sleeping_tiles)
            visible_q = (
                self.world.rest_quality_at(visible_rest) if visible_rest else 0.0
            )
        else:
            visible_rest = None
            visible_q = 0.0
        agent.update_rest_target(
            visible_rest, visible_q, sleeping_tiles, is_night, tick_count
        )

        rest_target = agent.rest_target
        old_pos = agent.pos
        at_rest_target = rest_target is None or agent.pos == rest_target
        was_sleeping = agent.is_sleeping

        if agent.continue_sleeping():
            agent.planned_steps.clear()
            agent.move_to(agent.pos)
            agent.next_decision_tick = tick_count + 1
        elif self._should_continue_harvesting(agent):
            agent.planned_steps.clear()
            agent.move_to(agent.pos)
            agent.next_decision_tick = tick_count + 1
        else:
            planned = self._plan_steps(
                agent,
                candidates,
                food_targets,
                vision,
                is_night,
                occupied,
                tick_count,
                rest_target=rest_target,
                visible_water=visible_water,
            )

            if agent.try_fall_asleep(
                at_rest_target, self.world.rivers.is_river_tile(agent.pos)
            ):
                agent.planned_steps.clear()
                agent.move_to(agent.pos)
                agent.next_decision_tick = tick_count + 1
            else:
                agent.move_to(planned[0])
                agent.planned_steps = planned[1:]
                agent.next_decision_tick = tick_count + len(planned)

        if was_sleeping and not agent.is_sleeping:
            agent.update_rest_memory(agent.pos, tile_quality, tick_count)
            agent.rest_target = None

        if profiling:
            task_name = agent.active_task.name if agent.active_task else "explore"
            tick_task_counts[task_name] = tick_task_counts.get(task_name, 0) + 1

        occupied.discard(old_pos)
        occupied.add(agent.pos)
        agent.age += 1

        new_pos = agent.pos

        if new_pos != old_pos and not agent.is_sleeping:
            elev_gain = self.world.elevation_at(new_pos) - self.world.elevation_at(
                old_pos
            )
            if elev_gain > 0:
                agent.drain_uphill(elev_gain)

        ate_this_tick = self._tick_harvest(agent, events)

        if self.world.rivers.is_river_tile(agent.pos):
            agent.drink()
            events.append(("agent_drank", {"agent_id": str(agent.id)}))

        if not ate_this_tick and not agent.is_sleeping:
            agent.apply_hunger_drain(self.world.rivers.is_river_tile(agent.pos))

        events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

        return agent.should_die()

    def _execute_agent_step(
        self,
        agent: Agent,
        occupied: set[Pos],
        sleeping_tiles: set[Pos],
        events: list[tuple[str, dict]],
        tick_count: int,
        is_night: bool,
    ) -> bool:
        """Execute a pre-planned step for one agent. Returns True if agent should die."""
        ax, ay = agent.x, agent.y
        tile_quality = self.world.rest_quality_at(agent.pos)
        shade = self.vegetation.shade_at(ax, ay)
        temperature = cfg.temp_to_c(
            max(
                0.0,
                self.world.weather.temperature_grid[ay * self.world.width + ax] - shade,
            )
        )
        agent.tick_needs(is_night, tile_quality=tile_quality, temperature=temperature)

        old_pos = agent.pos
        was_sleeping = agent.is_sleeping

        if agent.continue_sleeping():
            agent.planned_steps.clear()
            agent.move_to(agent.pos)
        elif self._should_continue_harvesting(agent):
            agent.planned_steps.clear()
            agent.move_to(agent.pos)
            agent.next_decision_tick = tick_count + 1
        else:
            if was_sleeping:
                # Just woke up — clear stale plan, re-decide next tick
                agent.planned_steps.clear()
                agent.next_decision_tick = tick_count
                agent.move_to(agent.pos)
            elif agent.planned_steps:
                step = agent.planned_steps[0]
                if step != agent.pos and step in occupied:
                    # Blocked by another agent — force immediate re-decision
                    agent.planned_steps.clear()
                    agent.next_decision_tick = tick_count
                    agent.move_to(agent.pos)
                else:
                    agent.planned_steps.pop(0)
                    if agent.path and agent.path[0] == step:
                        agent.path.pop(0)
                    agent.move_to(step)
                    # Fall asleep if task is sleep and we just arrived at rest target
                    at_rest_target = (
                        agent.rest_target is None or agent.pos == agent.rest_target
                    )
                    if agent.try_fall_asleep(
                        at_rest_target, self.world.rivers.is_river_tile(agent.pos)
                    ):
                        agent.planned_steps.clear()
            else:
                # Plan exhausted — re-decide next tick
                agent.next_decision_tick = tick_count
                agent.move_to(agent.pos)

        if was_sleeping and not agent.is_sleeping:
            agent.update_rest_memory(agent.pos, tile_quality, tick_count)
            agent.rest_target = None

        occupied.discard(old_pos)
        occupied.add(agent.pos)
        agent.age += 1

        new_pos = agent.pos

        if new_pos != old_pos and not agent.is_sleeping:
            elev_gain = self.world.elevation_at(new_pos) - self.world.elevation_at(
                old_pos
            )
            if elev_gain > 0:
                agent.drain_uphill(elev_gain)

        ate_this_tick = self._tick_harvest(agent, events)

        if self.world.rivers.is_river_tile(agent.pos):
            agent.drink()
            events.append(("agent_drank", {"agent_id": str(agent.id)}))

        if not ate_this_tick and not agent.is_sleeping:
            agent.apply_hunger_drain(self.world.rivers.is_river_tile(agent.pos))

        events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

        return agent.should_die()

    def on_tick(self, tick_count: int) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        is_night = (tick_count % DAY_LENGTH) >= DAY_LENGTH // 2
        self.world.weather.set_day_phase((tick_count % DAY_LENGTH) / DAY_LENGTH)
        # temperature_grid is rebuilt inside set_day_phase

        self.vegetation.grow_plants(tick_count, events)

        all_living = self.agents.all_living
        agent_vision = {a.id: float(a.vision_range) for a in all_living}
        agent_plants = self.vegetation.compute_plant_visibility(
            agent_vision, self.agents
        )

        occupied: set[Pos] = {a.pos for a in all_living}
        sleeping_tiles: set[Pos] = {a.pos for a in all_living if a.is_sleeping}

        self.agents.build_spatial_grid()

        deciding = [a for a in all_living if tick_count >= a.next_decision_tick]
        executing = [a for a in all_living if tick_count < a.next_decision_tick]

        profiling = self._PROFILE_START <= tick_count <= self._PROFILE_END
        tick_task_counts: dict[str, int] = {}

        dead = []

        for agent in executing:
            if self._execute_agent_step(
                agent, occupied, sleeping_tiles, events, tick_count, is_night
            ):
                dead.append(agent.id)

        for agent in deciding:
            if self._decide_agent_step(
                agent,
                agent_vision,
                agent_plants,
                occupied,
                sleeping_tiles,
                events,
                tick_count,
                is_night,
                profiling,
                tick_task_counts,
            ):
                dead.append(agent.id)

        if profiling:
            for name, count in tick_task_counts.items():
                self._task_counts[name] = self._task_counts.get(name, 0) + count
            self._profile_ticks += 1

        if tick_count == self._PROFILE_END:
            self._write_task_chart()

        for agent_id in dead:
            events.extend(self.agents.process_agent_death(agent_id))

        eligible_pairs = reproduce(self.world, self.agents, events, tick_count)

        living = self.agents.all_living
        plant_count = len(self.vegetation.all_plants)
        self._metrics.record_tick(living, plant_count, eligible_pairs)

        for event_type, data in events:
            self._metrics.record_event(event_type, data)

        if not living and not self._game_logged:
            self._metrics.write_game_log()
            self._game_logged = True

        self.world.weather.tick()

        return events

    def _write_task_chart(self) -> None:
        if not self._profile_ticks:
            return

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        order = ["explore", "seek_food", "drink", "sleep", "mate"]
        tasks = [t for t in order if t in self._task_counts] + [
            t for t in self._task_counts if t not in order
        ]
        averages = [self._task_counts[t] / self._profile_ticks for t in tasks]

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(tasks, averages, color="steelblue")
        ax.bar_label(bars, fmt="%.1f", padding=3)
        ax.set_xlabel("Task")
        ax.set_ylabel("Avg agents per tick")
        ax.set_title(
            f"Task distribution — ticks {self._PROFILE_START}–{self._PROFILE_END} "
            f"({self._profile_ticks} samples)"
        )
        ax.set_ylim(0, max(averages) * 1.15)
        plt.tight_layout()

        out = Path("/app/logs/task_profile.png")
        fig.savefig(out, dpi=150)
        plt.close(fig)
        print(f"[profile] Task chart saved → {out}")
