import random
from collections import defaultdict
from agent import Agent
from clock import DAY_LENGTH
from ecology import FOOD_REGROW_TICKS, form_groups
from food import Food
from group import Group
from metrics import SimulationMetrics
from movement import best_move, effective_vision, lone_social_target
from pathfinding import astar
from reproduction import reproduce
from world import World, world

MAX_AGE = 300


class Simulation:
    def __init__(self, w: World) -> None:
        self.world = w
        self._regrow_queue: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self._metrics = SimulationMetrics(max_age=MAX_AGE)
        self._game_logged: bool = False

    def save_log(self) -> None:
        if not self._game_logged and self._metrics._ticks > 0:
            self._metrics.write_game_log()
            self._game_logged = True

    def reset(self) -> None:
        self._regrow_queue.clear()
        self._metrics.reset()
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
        occupied: set[tuple[int, int]] | None = None,
        tick_count: int = 0,
    ) -> tuple[int, int]:
        food_goal_still_valid = bool(
            agent.active_task
            and agent.active_task.name == "seek_food"
            and self.world.get_food_at(*agent.active_task.goal_pos)
        )
        queue = agent.build_task_queue(
            food_targets,
            self._find_mate_target(agent, vision),
            agent.explore_goal(self.world.width, self.world.height),
            food_goal_still_valid,
        )
        top_task = queue[0]

        replan = (
            agent.active_task is None
            or top_task.name != agent.active_task.name
            or top_task.goal_pos != agent.active_task.goal_pos
            or not agent.path
        )

        if replan:
            agent.path = astar(self.world, (agent.x, agent.y), top_task.goal_pos, occupied)
            agent.active_task = top_task

        if agent.path:
            step = agent.path[0]
            if step in candidates:
                agent.path.pop(0)
                return step
            agent.path = astar(self.world, (agent.x, agent.y), top_task.goal_pos, occupied)
            if agent.path and agent.path[0] in candidates:
                return agent.path.pop(0)
            # Both path attempts blocked — tiebreaker: alternate which agent waits vs advances
            # each tick so deadlocked pairs don't mirror each other indefinitely
            if (agent.id.int + tick_count) % 2 == 0:
                return (agent.x, agent.y)

        return best_move(self.world, agent, candidates, food_targets, group, social_target)

    def on_tick(self, tick_count: int) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        is_night = (tick_count % DAY_LENGTH) >= DAY_LENGTH // 2

        for pos in self._regrow_queue.pop(tick_count, []):
            x, y = pos
            if not self.world.is_river_tile(x, y) and self.world.get_food_at(x, y) is None:
                food = self.world.place_food(x, y)
                events.append(("food_grew", {"food": food.model_dump(mode="json")}))

        self.world.update_group_centers()

        agent_vision = {a.id: effective_vision(self.world, a) for a in self.world.all_living_agents()}
        agent_food = self.world.compute_food_visibility(agent_vision)
        events.extend(self.world.prune_groups())

        occupied: set[tuple[int, int]] = {(a.x, a.y) for a in self.world.all_living_agents()}

        dead = []
        for agent in sorted(self.world.all_living_agents(), key=lambda a: a.health):
            moves = self.world.valid_moves(agent.x, agent.y, own_home=agent.home_pos)
            if not moves:
                continue

            candidates = [m for m in moves if m not in occupied]
            if not candidates:
                continue

            group = self.world.group_for_agent(agent.id)
            food_targets = [f for f in agent_food.get(agent.id, []) if self.world.get_food_at(f.x, f.y)]

            agent.update_food_memory(food_targets)

            social_target = (
                None if group
                else lone_social_target(self.world, agent, agent_vision[agent.id])
            )

            agent.tick_rest(is_night)

            nav_food_targets = [] if agent.carried_food is not None else food_targets
            old_pos = (agent.x, agent.y)
            if agent.should_rest():
                agent.move_to(agent.x, agent.y)
            else:
                agent.move_to(*self._next_pos(
                    agent, candidates, nav_food_targets, group, social_target, agent_vision[agent.id], occupied, tick_count
                ))
            occupied.discard(old_pos)
            occupied.add((agent.x, agent.y))
            agent.age += 1

            ate_this_tick = False
            food = self.world.consume_food_at(agent.x, agent.y) if agent.carried_food is None else None
            if food:
                self._regrow_queue[tick_count + FOOD_REGROW_TICKS].append((agent.x, agent.y))
                if agent.home_pos is None:
                    pending_regrow = {pos for positions in self._regrow_queue.values() for pos in positions}
                    home_tile = self.world.find_home_tile(food.x, food.y, pending_regrow)
                    if home_tile:
                        home = self.world.place_home(agent.id, *home_tile)
                        agent.home_pos = home_tile
                        events.append(("home_built", {"home": home.model_dump(mode="json")}))
                    agent.eat()
                    ate_this_tick = True
                    events.append(("agent_ate", {
                        "agent": agent.model_dump(mode="json"),
                        "food_id": str(food.id),
                    }))
                else:
                    agent.carried_food = food
                    events.append(("agent_picked_up_food", {
                        "agent": agent.model_dump(mode="json"),
                        "food_id": str(food.id),
                    }))

            if not ate_this_tick and agent.carried_food is not None and (agent.x, agent.y) == agent.home_pos:
                food_id = str(agent.carried_food.id)
                agent.carried_food = None
                agent.eat()
                ate_this_tick = True
                events.append(("agent_ate", {
                    "agent": agent.model_dump(mode="json"),
                    "food_id": food_id,
                }))

            if not ate_this_tick:
                agent.apply_hunger_drain(
                    self.world.is_river_tile(agent.x, agent.y),
                    agent.group_id is None,
                )

            events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

            if agent.health <= 0 or agent.age >= MAX_AGE:
                dead.append(agent.id)

        for agent_id in dead:
            events.extend(self.world.process_agent_death(agent_id))

        form_groups(self.world, events)
        eligible_pairs = reproduce(self.world, events, tick_count)

        living = self.world.all_living_agents()
        food_count = sum(1 for _ in self.world.all_food())
        self._metrics.record_tick(living, len(self.world.all_groups()), food_count, eligible_pairs)

        for event_type, data in events:
            self._metrics.record_event(event_type, data)

        if not living and not self._game_logged:
            self._metrics.write_game_log()
            self._game_logged = True

        return events


simulation = Simulation(world)
