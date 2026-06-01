import random

from agents import Agents
from agents.agent import Agent
from clock import DAY_LENGTH
from food import FoodManager
from group import Group
from metrics import SimulationMetrics
from movement import best_move, effective_vision, lone_social_target
from pos import Pos
from tasks import Task
from pathfinding import astar
from agents.reproduction import reproduce
import config as cfg
from world import World
from food import FoodItem


class Simulation:
    def __init__(self, world: World, food: FoodManager, agents: Agents) -> None:
        self.world = world
        self.food = food
        self.agents = agents
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
        self._metrics = SimulationMetrics(max_age=cfg.MAX_AGE)
        self._game_logged = False
        self.world.reset()
        self.food.reset()
        self.agents.reset()

    def _next_pos(
        self,
        agent: Agent,
        candidates: list[Pos],
        food_targets: list[FoodItem],
        group: Group | None,
        social_target: tuple[float, float, float] | None,
        vision: float,
        is_night: bool,
        occupied: set[Pos] | None = None,
        tick_count: int = 0,
        rest_target: Pos | None = None,
        visible_water: list[Pos] | None = None,
    ) -> Pos:
        top_task = agent.choose_action(
            is_night,
            self.agents.find_mate_target(agent, vision, tick_count),
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

        if agent.path:
            step = agent.path[0]
            if step in candidates:
                agent.path.pop(0)
                return step
            agent.path = astar(
                self.world, agent.pos, top_task.goal_pos, occupied, int(vision)
            )
            if agent.path and agent.path[0] in candidates:
                return agent.path.pop(0)
            if (agent.id.int + tick_count) % 2 == 0:
                return agent.pos
        elif top_task.name == "sleep":
            return agent.pos

        return best_move(agent, candidates, food_targets, group, social_target)

    def on_tick(self, tick_count: int) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        is_night = (tick_count % DAY_LENGTH) >= DAY_LENGTH // 2

        self.food.process_regrow(tick_count, events)

        self.agents.update_group_centers()

        all_living = self.agents.all_living
        agent_vision = {a.id: effective_vision(self.agents, a) for a in all_living}
        agent_food = self.food.compute_food_visibility(agent_vision, self.agents)

        events.extend(self.agents.prune_groups())

        occupied: set[Pos] = {a.pos for a in all_living}
        sleeping_tiles: set[Pos] = {a.pos for a in all_living if a.is_sleeping}

        dead = []
        for agent in all_living:
            moves = self.world.valid_moves(agent.pos)
            if not moves:
                continue

            candidates = [m for m in moves if m not in occupied]
            if not candidates:
                continue

            group = self.agents.group_for_agent(agent.id)
            food_targets = [
                f for f in agent_food.get(agent.id, []) if self.food.get_food_at(f.pos)
            ]

            # update food memory
            if (
                agent.active_task is not None
                and agent.active_task.name == "seek_food"
                and agent.path
            ):
                nearby = [
                    f
                    for f in food_targets
                    if abs(f.x - agent.x) + abs(f.y - agent.y) <= 5
                ]
                if nearby:
                    food_targets = nearby

            agent.update_food_memory(food_targets, tick_count)

            vision = agent_vision[agent.id]
            vision_int = int(vision)
            ax, ay = agent.x, agent.y
            visible_water = [
                pos
                for pos in self.world.rivers.all_tiles
                if abs(pos.x - ax) <= vision_int
                and abs(pos.y - ay) <= vision_int
                and abs(pos.x - ax) + abs(pos.y - ay) <= vision_int
            ]
            agent.update_water_memory(visible_water, tick_count)

            social_target = (
                None if group else lone_social_target(self.agents, agent, vision)
            )

            tile_quality = self.world.rest_quality_at(agent.pos)
            temperature = self.world.weather.temperature_at(agent.pos.x, agent.pos.y)
            agent.tick_needs(
                is_night, tile_quality=tile_quality, temperature=temperature
            )

            visible_rest = self.world.best_rest_in_vision(agent, 10, sleeping_tiles)
            visible_q = (
                self.world.rest_quality_at(visible_rest) if visible_rest else 0.0
            )
            agent.update_rest_target(
                visible_rest, visible_q, sleeping_tiles, is_night, tick_count
            )

            rest_target = agent.rest_target
            old_pos = agent.pos
            at_rest_target = rest_target is None or agent.pos == rest_target
            was_sleeping = agent.is_sleeping

            if agent.continue_sleeping():
                agent.move_to(agent.pos)
            else:
                new_pos = self._next_pos(
                    agent,
                    candidates,
                    food_targets,
                    group,
                    social_target,
                    vision,
                    is_night,
                    occupied,
                    tick_count,
                    rest_target=rest_target,
                    visible_water=visible_water,
                )

                if agent.try_fall_asleep(at_rest_target):
                    agent.move_to(agent.pos)
                else:
                    agent.move_to(new_pos)

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

            ate_this_tick = False
            consumed = self.food.remove_food_at(agent.pos)

            if consumed:
                self.food.schedule_regrow(agent.pos, tick_count)
                agent.eat()
                ate_this_tick = True
                events.append(
                    (
                        "agent_ate",
                        {
                            "agent": agent.model_dump(mode="json"),
                            "food_id": str(consumed.id),
                        },
                    )
                )

            if self.world.rivers.is_river_tile(agent.pos):
                agent.drink()
                events.append(("agent_drank", {"agent_id": str(agent.id)}))

            if not ate_this_tick and not agent.is_sleeping:
                agent.apply_hunger_drain(
                    self.world.rivers.is_river_tile(agent.pos),
                    agent.group_id is None,
                )

            events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

            if agent.should_die():
                dead.append(agent.id)

        for agent_id in dead:
            events.extend(self.agents.process_agent_death(agent_id))

        self.agents.form_groups(events)
        eligible_pairs = reproduce(self.world, self.agents, events, tick_count)

        living = self.agents.all_living
        food_count = len(self.food.all_food)
        self._metrics.record_tick(
            living, len(self.agents.all_groups), food_count, eligible_pairs
        )

        for event_type, data in events:
            self._metrics.record_event(event_type, data)

        if not living and not self._game_logged:
            self._metrics.write_game_log()
            self._game_logged = True

        self.world.weather.tick()

        return events
