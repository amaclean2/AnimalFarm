from collections import defaultdict
from uuid import UUID

from agent import MAX_HEALTH
from ecology import FOOD_REGROW_TICKS, form_groups, reproduce
from food import Food
from metrics import SimulationMetrics
from movement import LONE_HEALTH_PENALTY, STOCKPILE_HUNGER_THRESHOLD, effective_vision, lone_social_target, score_move
from world import World, world

MAX_AGE = 200
INFANT_DRAIN = 5
MATURITY_AGE = 40


def starvation_drain(age: int) -> int:
    """Higher drain when young, tapering linearly to 1 at MATURITY_AGE."""
    t = min(age, MATURITY_AGE) / MATURITY_AGE
    return max(1, round(INFANT_DRAIN + (1 - INFANT_DRAIN) * t))


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
                    member.carrying_food = False
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
            food_targets = agent_food.get(agent.id, [])

            if food_targets:
                nearest = min(food_targets, key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y))
                agent.last_food_seen = (nearest.x, nearest.y)

            social_target = (
                None if group
                else lone_social_target(self.world, agent, agent_vision[agent.id])
            )

            old_pos = (agent.x, agent.y)
            agent.x, agent.y = max(
                candidates,
                key=lambda pos: score_move(agent, pos, food_targets, group, social_target),
            )
            agent.direction = (agent.x - old_pos[0], agent.y - old_pos[1])
            occupied.discard(old_pos)
            occupied.add((agent.x, agent.y))
            agent.age += 1

            food = self.world.consume_food_at(agent.x, agent.y)
            if food:
                self._regrow_queue[tick_count + FOOD_REGROW_TICKS].append((agent.x, agent.y))
                if agent.health >= MAX_HEALTH * 0.90 and not agent.carrying_food and group and group.home:
                    agent.carrying_food = True
                    events.append(("agent_picked_up_food", {"agent": agent.model_dump(mode="json")}))
                else:
                    agent.health = MAX_HEALTH
                    agent.direction = None
                    events.append(("agent_ate", {
                        "agent": agent.model_dump(mode="json"),
                        "food_id": str(food.id),
                    }))
            else:
                agent.health -= round(starvation_drain(agent.age) * agent.metabolism) + (LONE_HEALTH_PENALTY if agent.group_id is None else 0)

            if agent.carrying_food and group and group.home:
                if (agent.x, agent.y) == group.home:
                    group.stockpile += 1
                    agent.carrying_food = False
                    events.append(("food_deposited", {"group_id": str(group.id), "stockpile": group.stockpile}))

            if not agent.carrying_food and group and group.home and group.stockpile > 0:
                near_home = abs(agent.x - group.home[0]) + abs(agent.y - group.home[1]) <= 1
                if agent.health < MAX_HEALTH * STOCKPILE_HUNGER_THRESHOLD and near_home:
                    group.stockpile -= 1
                    agent.health = MAX_HEALTH
                    agent.direction = None
                    events.append(("food_withdrawn", {"group_id": str(group.id), "stockpile": group.stockpile}))

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
