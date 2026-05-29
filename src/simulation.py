import random
from collections import defaultdict
from agent import Agent
from clock import DAY_LENGTH
from ecology import FOOD_REGROW_TICKS, form_groups
from food import Food
from group import Group
from metrics import SimulationMetrics
from movement import best_move, effective_vision, lone_social_target
from tasks import Task
from pathfinding import astar
from reproduction import reproduce
import config as cfg
from world import World, world


class Simulation:
    def __init__(self, w: World) -> None:
        self.world = w
        self._regrow_queue: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged: bool = False

    def save_log(self) -> None:
        if not self._game_logged and self._metrics._ticks > 0:
            self._metrics.write_game_log()
            self._game_logged = True

    def prepare(self) -> None:
        """Reinitialize metrics with the current runtime config before a new game starts."""
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged = False

    def reset(self) -> None:
        self._regrow_queue.clear()
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged = False
        self.world.reset()

    def _find_mate_target(self, agent: Agent, vision: float) -> tuple[int, int] | None:
        if not agent.is_eligible_to_mate():
            return None
        best: tuple[int, int] | None = None
        best_dist = float("inf")
        for other in self.world.agents_in_range(agent, vision):
            if not other.is_eligible_to_mate():
                continue
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            if dist < best_dist:
                best_dist = dist
                best = (other.x, other.y)
        return best

    def _next_pos(
        self,
        agent: Agent,
        candidates: list[tuple[int, int]],
        food_targets: list[Food],
        group: Group | None,
        social_target: tuple[float, float, float] | None,
        vision: float,
        is_night: bool,
        occupied: set[tuple[int, int]] | None = None,
        tick_count: int = 0,
        rest_target: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        top_task = agent.choose_action(
            is_night,
            self._find_mate_target(agent, vision),
            agent.explore_goal(self.world.width, self.world.height, tick_count),
            tick_count,
            rest_target=rest_target,
        )

        if top_task.name == "seek_food" and food_targets:
            nearest = min(
                food_targets,
                key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y),
            )
            top_task = Task(
                priority=top_task.priority,
                name="seek_food",
                goal_pos=(nearest.x, nearest.y),
            )

        if top_task.name == "drink":
            visible_water = [
                pos
                for pos in self.world.all_river_tiles()
                if abs(pos[0] - agent.x) + abs(pos[1] - agent.y) <= vision
            ]
            if visible_water:
                nearest_water = min(
                    visible_water,
                    key=lambda pos: abs(pos[0] - agent.x) + abs(pos[1] - agent.y),
                )
                top_task = Task(
                    priority=top_task.priority,
                    name="drink",
                    goal_pos=nearest_water,
                )

        replan = (
            agent.active_task is None
            or top_task.name != agent.active_task.name
            or top_task.goal_pos != agent.active_task.goal_pos
            or not agent.path
        )

        if replan:
            agent.path = astar(
                self.world, (agent.x, agent.y), top_task.goal_pos, occupied
            )
            agent.active_task = top_task

        if agent.path:
            step = agent.path[0]
            if step in candidates:
                agent.path.pop(0)
                return step
            agent.path = astar(
                self.world, (agent.x, agent.y), top_task.goal_pos, occupied
            )
            if agent.path and agent.path[0] in candidates:
                return agent.path.pop(0)
            # Both path attempts blocked — tiebreaker: alternate which agent waits vs advances
            # each tick so deadlocked pairs don't mirror each other indefinitely
            if (agent.id.int + tick_count) % 2 == 0:
                return (agent.x, agent.y)
        elif top_task.name == "sleep":
            # No path to sleep target (unreachable) — stay put rather than wandering
            return (agent.x, agent.y)

        return best_move(agent, candidates, food_targets, group, social_target)

    def on_tick(self, tick_count: int) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        is_night = (tick_count % DAY_LENGTH) >= DAY_LENGTH // 2

        for pos in self._regrow_queue.pop(tick_count, []):
            x, y = pos
            if (
                not self.world.is_river_tile(x, y)
                and self.world.get_food_at(x, y) is None
            ):
                food = self.world.place_food(x, y)
                events.append(("food_grew", {"food": food.model_dump(mode="json")}))

        self.world.update_group_centers()

        agent_vision = {
            a.id: effective_vision(self.world, a)
            for a in self.world.all_living_agents()
        }
        agent_food = self.world.compute_food_visibility(agent_vision)
        events.extend(self.world.prune_groups())

        occupied: set[tuple[int, int]] = {
            (a.x, a.y) for a in self.world.all_living_agents()
        }
        sleeping_tiles: set[tuple[int, int]] = {
            (a.x, a.y) for a in self.world.all_living_agents() if a.is_sleeping
        }

        dead = []
        for agent in self.world.all_living_agents():
            moves = self.world.valid_moves(agent.x, agent.y)
            if not moves:
                continue

            candidates = [m for m in moves if m not in occupied]
            if not candidates:
                continue

            group = self.world.group_for_agent(agent.id)
            food_targets = [
                f
                for f in agent_food.get(agent.id, [])
                if self.world.get_food_at(f.x, f.y)
            ]

            agent.update_food_memory(food_targets, tick_count)

            vision = agent_vision[agent.id]
            for pos in self.world.all_river_tiles():
                if abs(pos[0] - agent.x) + abs(pos[1] - agent.y) <= vision:
                    agent.memory.observe(pos, "water", 1.0, tick_count)

            social_target = (
                None
                if group
                else lone_social_target(self.world, agent, agent_vision[agent.id])
            )

            tile_quality = self.world.rest_quality_at(agent.x, agent.y)
            temperature = self.world.temperature_at(agent.x, agent.y)
            agent.tick_needs(
                is_night, tile_quality=tile_quality, temperature=temperature
            )

            drain_rate = cfg.REST_BASE_DRAIN * (
                cfg.REST_NIGHT_MULTIPLIER if is_night else 1.0
            )
            safety = cfg.REST_SAFETY_BUFFER_FRAC
            usable = max(0.0, agent.needs.rest - safety)
            max_travel = max(1, int(usable / drain_rate))

            visible_rest = self.world.best_rest_in_vision(agent, vision, sleeping_tiles)
            memory_rest = agent.memory.query("rest", tick_count, familiarity=True)

            if memory_rest is not None:
                mem_dist = abs(agent.x - memory_rest[0]) + abs(agent.y - memory_rest[1])
                if mem_dist > max_travel or memory_rest in sleeping_tiles:
                    memory_rest = None

            rest_target: tuple[int, int] | None = None

            if visible_rest and memory_rest:
                visible_q = self.world.rest_quality_at(*visible_rest)
                mem_q = self.world.rest_quality_at(*memory_rest)
                mem_dist = abs(agent.x - memory_rest[0]) + abs(agent.y - memory_rest[1])
                decay = max(0.0, 1.0 - mem_dist / max(max_travel, 1))
                mem_score = mem_q + cfg.MEMORY_REST_BONUS * decay
                rest_target = memory_rest if mem_score >= visible_q else visible_rest
            elif visible_rest:
                rest_target = visible_rest
            elif memory_rest:
                rest_target = memory_rest

            old_pos = (agent.x, agent.y)
            at_rest_target = rest_target is None or (agent.x, agent.y) == rest_target

            was_sleeping = agent.is_sleeping

            if was_sleeping and agent.needs.rest < 1.0:
                agent.needs.is_sleeping = True
                agent.move_to(agent.x, agent.y)
            else:
                agent.needs.is_sleeping = False
                new_pos = self._next_pos(
                    agent,
                    candidates,
                    food_targets,
                    group,
                    social_target,
                    agent_vision[agent.id],
                    is_night,
                    occupied,
                    tick_count,
                    rest_target=rest_target,
                )

                if (
                    agent.active_task
                    and agent.active_task.name == "sleep"
                    and at_rest_target
                ):
                    agent.needs.is_sleeping = True
                    agent.move_to(agent.x, agent.y)
                else:
                    agent.move_to(*new_pos)

            if was_sleeping and not agent.is_sleeping:
                agent.update_rest_memory((agent.x, agent.y), tile_quality, tick_count)
            occupied.discard(old_pos)
            occupied.add((agent.x, agent.y))
            agent.age += 1

            new_pos = (agent.x, agent.y)
            if new_pos != old_pos and not agent.is_sleeping:
                elev_gain = self.world.elevation_at(*new_pos) - self.world.elevation_at(
                    *old_pos
                )
                if elev_gain > 0:
                    agent.drain_uphill(elev_gain)

            ate_this_tick = False
            food = self.world.consume_food_at(agent.x, agent.y)
            if food:
                self._regrow_queue[tick_count + FOOD_REGROW_TICKS].append(
                    (agent.x, agent.y)
                )
                agent.eat()
                ate_this_tick = True
                events.append(
                    (
                        "agent_ate",
                        {
                            "agent": agent.model_dump(mode="json"),
                            "food_id": str(food.id),
                        },
                    )
                )

            if self.world.is_river_tile(agent.x, agent.y):
                agent.drink()
                events.append(("agent_drank", {"agent_id": str(agent.id)}))

            if not ate_this_tick and not agent.is_sleeping:
                agent.apply_hunger_drain(
                    self.world.is_river_tile(agent.x, agent.y),
                    agent.group_id is None,
                )

            events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

            if agent.hunger <= 0 or agent.needs.rest <= 0 or agent.age >= cfg.MAX_AGE:
                dead.append(agent.id)

        for agent_id in dead:
            events.extend(self.world.process_agent_death(agent_id))

        form_groups(self.world, events)
        eligible_pairs = reproduce(self.world, events, tick_count)

        living = self.world.all_living_agents()
        food_count = sum(1 for _ in self.world.all_food())
        self._metrics.record_tick(
            living, len(self.world.all_groups()), food_count, eligible_pairs
        )

        for event_type, data in events:
            self._metrics.record_event(event_type, data)

        if not living and not self._game_logged:
            self._metrics.write_game_log()
            self._game_logged = True

        return events


simulation = Simulation(world)
