import heapq
import math
import random
from collections import defaultdict
from uuid import UUID

from agent import Agent, MAX_HEALTH
from ecology import FOOD_REGROW_TICKS, form_groups
from food import Food
from group import Group
from metrics import SimulationMetrics
from movement import LONE_HEALTH_PENALTY, best_move, effective_vision, lone_social_target
from pathfinding import astar
from reproduction import reproduce, REPRODUCTION_HEALTH_THRESHOLD, REPRODUCTION_MATURITY_AGE
from tasks import Task, PRIORITY_SEEK_FOOD, PRIORITY_MATE, PRIORITY_EXPLORE
from world import World, world

MAX_AGE = 200
INFANT_DRAIN = 5
MATURITY_AGE = 30
WATER_DRAIN_MULTIPLIER = 2


def starvation_drain(age: int, is_adult: bool = False) -> int:
    """Higher drain when young, tapering linearly to 1 at MATURITY_AGE."""
    if is_adult:
        return 1
    t = min(age, MATURITY_AGE) / MATURITY_AGE
    return max(1, round(INFANT_DRAIN + (1 - INFANT_DRAIN) * t))


class Simulation:
    def __init__(self, w: World) -> None:
        self.world = w
        self._regrow_queue: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self._metrics = SimulationMetrics(max_age=MAX_AGE)
        self._game_logged: bool = False
        self._agent_active_tasks: dict[UUID, Task] = {}
        self._agent_paths: dict[UUID, list[tuple[int, int]]] = {}

    def save_log(self) -> None:
        if not self._game_logged and self._metrics._ticks > 0:
            self._metrics.write_game_log()
            self._game_logged = True

    def reset(self) -> None:
        self._regrow_queue.clear()
        self._metrics.reset()
        self._game_logged = False
        self._agent_active_tasks.clear()
        self._agent_paths.clear()
        self.world.reset()

    def _explore_goal(self, agent: Agent) -> tuple[int, int]:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(10, 25)
        ex = max(0, min(self.world.width - 1, int(agent.x + dist * math.cos(angle))))
        ey = max(0, min(self.world.height - 1, int(agent.y + dist * math.sin(angle))))
        return (ex, ey)

    def _find_mate_target(self, agent: Agent, vision: float) -> tuple[int, int] | None:
        if agent.age < REPRODUCTION_MATURITY_AGE:
            return None
        min_health = int(MAX_HEALTH * REPRODUCTION_HEALTH_THRESHOLD)
        if agent.health < min_health:
            return None

        best: tuple[int, int] | None = None
        best_dist = float("inf")
        for other in self.world.agents_in_range(agent, vision):
            if other.age < REPRODUCTION_MATURITY_AGE:
                continue
            if other.health < min_health:
                continue
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            if dist < best_dist:
                best_dist = dist
                best = (other.x, other.y)
        return best

    def _build_task_queue(
        self, agent: Agent, food_targets: list[Food], group: Group | None, vision: float
    ) -> list[Task]:
        queue: list[Task] = []
        active = self._agent_active_tasks.get(agent.id)
        path = self._agent_paths.get(agent.id, [])

        if food_targets:
            nearest = min(food_targets, key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y))
            food_goal = (nearest.x, nearest.y)
            if active and active.name == "seek_food":
                curr_dist = abs(agent.x - active.goal_pos[0]) + abs(agent.y - active.goal_pos[1])
                new_dist = abs(nearest.x - agent.x) + abs(nearest.y - agent.y)
                if new_dist >= curr_dist - 3 and self.world.get_food_at(*active.goal_pos):
                    food_goal = active.goal_pos
            heapq.heappush(queue, Task(PRIORITY_SEEK_FOOD, "seek_food", food_goal))
        elif agent.last_food_seen:
            heapq.heappush(queue, Task(PRIORITY_SEEK_FOOD, "seek_food", agent.last_food_seen))

        mate_pos = self._find_mate_target(agent, vision)
        if mate_pos:
            heapq.heappush(queue, Task(PRIORITY_MATE, "mate", mate_pos))

        # preserve existing explore goal while a path remains
        if active and active.name == "explore" and path:
            explore_pos = active.goal_pos
        else:
            explore_pos = self._explore_goal(agent)
        heapq.heappush(queue, Task(PRIORITY_EXPLORE, "explore", explore_pos))

        return queue

    def _next_pos(
        self,
        agent: Agent,
        candidates: list[tuple[int, int]],
        food_targets: list[Food],
        group: Group | None,
        social_target: tuple[float, float, float] | None,
        vision: float,
    ) -> tuple[int, int]:
        queue = self._build_task_queue(agent, food_targets, group, vision)
        top_task = queue[0]

        active_task = self._agent_active_tasks.get(agent.id)
        path = self._agent_paths.get(agent.id, [])

        replan = (
            active_task is None
            or top_task.name != active_task.name
            or top_task.goal_pos != active_task.goal_pos
            or not path
        )

        if replan:
            path = astar(self.world, (agent.x, agent.y), top_task.goal_pos)
            self._agent_active_tasks[agent.id] = top_task

        if path:
            step = path[0]
            if step in candidates:
                path.pop(0)
                self._agent_paths[agent.id] = path
                return step
            path = astar(self.world, (agent.x, agent.y), top_task.goal_pos)
            if path and path[0] in candidates:
                step = path.pop(0)
                self._agent_paths[agent.id] = path
                return step

        self._agent_paths[agent.id] = path
        return best_move(self.world, agent, candidates, food_targets, group, social_target)

    def on_tick(self, tick_count: int) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []

        for pos in self._regrow_queue.pop(tick_count, []):
            x, y = pos
            if not self.world.is_river_tile(x, y) and self.world.get_food_at(x, y) is None:
                food = self.world.place_food(x, y)
                events.append(("food_grew", {"food": food.model_dump(mode="json")}))

        for group in self.world.all_groups():
            members = [
                self.world.get_agent(mid)
                for mid in group.member_ids
                if self.world.get_agent(mid) is not None
            ]
            group.update_center(members)

        agent_vision: dict[UUID, float] = {
            a.id: effective_vision(self.world, a) for a in self.world.all_living_agents()
        }

        group_shared_food: dict[UUID, list[Food]] = {}
        for group in self.world.all_groups():
            seen_ids: set[UUID] = set()
            shared: list[Food] = []
            for mid in group.member_ids:
                member = self.world.get_agent(mid)
                if not member:
                    continue
                for f in self.world.food_in_vision(member, agent_vision[mid]):
                    if f.id not in seen_ids:
                        seen_ids.add(f.id)
                        shared.append(f)
            group_shared_food[group.id] = shared

        agent_food: dict[UUID, list[Food]] = {}
        for agent in self.world.all_living_agents():
            group = self.world.group_for_agent(agent.id)
            agent_food[agent.id] = (
                group_shared_food[group.id] if group
                else self.world.food_in_vision(agent, agent_vision[agent.id])
            )

        for group in list(self.world.all_groups()):
            for mid in list(group.member_ids):
                member = self.world.get_agent(mid)
                if member is None:
                    group.member_ids.discard(mid)
                    continue
                dist = abs(member.x - group.center_x) + abs(member.y - group.center_y)
                if dist > group.attraction_range:
                    group.member_ids.discard(mid)
                    member.group_id = None
                    events.append(("agent_left_group", {
                        "agent_id": str(mid),
                        "group_id": str(group.id),
                    }))
            if group.size < 2:
                self.world.disband_group(group.id)
                events.append(("group_disbanded", {"group_id": str(group.id)}))

        occupied: set[tuple[int, int]] = {
            (a.x, a.y) for a in self.world.all_living_agents()
        }

        dead: list[UUID] = []
        for agent in sorted(self.world.all_living_agents(), key=lambda a: a.health):
            moves = self.world.valid_moves(agent.x, agent.y)
            if not moves:
                continue

            unoccupied = [m for m in moves if m not in occupied]
            candidates = unoccupied if unoccupied else moves

            group = self.world.group_for_agent(agent.id)
            food_targets = [f for f in agent_food.get(agent.id, []) if self.world.get_food_at(f.x, f.y)]

            if food_targets:
                nearest = min(food_targets, key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y))
                agent.last_food_seen = (nearest.x, nearest.y)
            elif agent.last_food_seen:
                mx, my = agent.last_food_seen
                if abs(agent.x - mx) + abs(agent.y - my) <= 2:
                    agent.last_food_seen = None

            social_target = (
                None if group
                else lone_social_target(self.world, agent, agent_vision[agent.id])
            )

            old_pos = (agent.x, agent.y)
            agent.x, agent.y = self._next_pos(
                agent, candidates, food_targets, group, social_target, agent_vision[agent.id]
            )
            agent.direction = (agent.x - old_pos[0], agent.y - old_pos[1])
            occupied.discard(old_pos)
            occupied.add((agent.x, agent.y))
            agent.age += 1

            food = self.world.consume_food_at(agent.x, agent.y)
            if food:
                self._regrow_queue[tick_count + FOOD_REGROW_TICKS].append((agent.x, agent.y))
                agent.health = MAX_HEALTH
                agent.direction = None
                events.append(("agent_ate", {
                    "agent": agent.model_dump(mode="json"),
                    "food_id": str(food.id),
                }))
            else:
                base_drain = round(starvation_drain(agent.age, agent.is_adult) * agent.metabolism)
                water_drain = base_drain * (WATER_DRAIN_MULTIPLIER - 1) if self.world.is_river_tile(agent.x, agent.y) else 0
                agent.health -= base_drain + water_drain + (LONE_HEALTH_PENALTY if agent.group_id is None else 0)

            events.append(("agent_moved", {"agent": agent.model_dump(mode="json")}))

            if agent.health <= 0 or agent.age >= MAX_AGE:
                dead.append(agent.id)

        for agent_id in dead:
            agent = self.world.get_agent(agent_id)
            if agent:
                agent.alive = False
                if agent.group_id:
                    group = self.world.group_for_agent(agent_id)
                    if group:
                        group.member_ids.discard(agent_id)
                        if group.size < 2:
                            self.world.disband_group(group.id)
                            events.append(("group_disbanded", {"group_id": str(group.id)}))
                events.append(("agent_died", {"agent": agent.model_dump(mode="json")}))
            self._agent_active_tasks.pop(agent_id, None)
            self._agent_paths.pop(agent_id, None)

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
