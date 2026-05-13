from collections import deque
from uuid import UUID

from agent import Agent
from food import Food
from group import Group
from home import Home
from river import River

_DIRECTIONS = [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]


class World:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._agents: dict[UUID, Agent] = {}
        self._food: dict[tuple[int, int], Food] = {}
        self._groups: dict[UUID, Group] = {}
        self._rivers: dict[UUID, River] = {}
        self._river_tiles: set[tuple[int, int]] = set()
        self._homes: dict[UUID, Home] = {}
        self._home_tiles: set[tuple[int, int]] = set()

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def valid_moves(self, x: int, y: int, own_home: tuple[int, int] | None = None) -> list[tuple[int, int]]:
        return [
            (x + dx, y + dy)
            for dx, dy in _DIRECTIONS
            if self.in_bounds(x + dx, y + dy)
            and (not self.is_home_tile(x + dx, y + dy) or (x + dx, y + dy) == own_home)
        ]

    def food_in_vision(self, agent: Agent, vision_range: float | None = None) -> list[Food]:
        r = vision_range if vision_range is not None else agent.vision_range
        return [
            f for f in self._food.values()
            if abs(f.x - agent.x) + abs(f.y - agent.y) <= r
        ]

    def agents_in_range(self, agent: Agent, range_val: float) -> list[Agent]:
        return [
            a for a in self._agents.values()
            if a.alive
            and a.id != agent.id
            and abs(a.x - agent.x) + abs(a.y - agent.y) <= range_val
        ]

    # --- Agents ---

    def add_agent(self, x: int, y: int, birth_tick: int = 0, age: int = 0) -> Agent:
        if not self.in_bounds(x, y):
            raise ValueError(f"Position ({x}, {y}) is out of bounds")
        agent = Agent(x=x, y=y, birth_tick=birth_tick, age=age)
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: UUID) -> Agent | None:
        return self._agents.get(agent_id)

    def remove_agent(self, agent_id: UUID) -> Agent | None:
        return self._agents.pop(agent_id, None)

    def all_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def all_living_agents(self) -> list[Agent]:
        return [a for a in self._agents.values() if a.alive]

    # --- Food ---

    def place_food(self, x: int, y: int, value: int = 1) -> Food:
        if not self.in_bounds(x, y):
            raise ValueError(f"Position ({x}, {y}) is out of bounds")
        if (x, y) in self._food:
            raise ValueError(f"Food already exists at ({x}, {y})")
        food = Food(x=x, y=y, value=value)
        self._food[(x, y)] = food
        return food

    def get_food_at(self, x: int, y: int) -> Food | None:
        return self._food.get((x, y))

    def get_food(self, food_id: UUID) -> Food | None:
        return next((f for f in self._food.values() if f.id == food_id), None)

    def remove_food(self, food_id: UUID) -> Food | None:
        food = self.get_food(food_id)
        if food:
            del self._food[(food.x, food.y)]
        return food

    def consume_food_at(self, x: int, y: int) -> Food | None:
        return self._food.pop((x, y), None)

    def all_food(self) -> list[Food]:
        return list(self._food.values())

    # --- Groups ---

    def add_group(self, member_ids: set[UUID]) -> Group:
        group = Group(member_ids=set(member_ids))
        for mid in member_ids:
            if mid in self._agents:
                self._agents[mid].group_id = group.id
        self._groups[group.id] = group
        return group

    def get_group(self, group_id: UUID) -> Group | None:
        return self._groups.get(group_id)

    def disband_group(self, group_id: UUID) -> Group | None:
        group = self._groups.pop(group_id, None)
        if group:
            for mid in group.member_ids:
                if mid in self._agents:
                    self._agents[mid].group_id = None
        return group

    def all_groups(self) -> list[Group]:
        return list(self._groups.values())

    def group_for_agent(self, agent_id: UUID) -> Group | None:
        agent = self._agents.get(agent_id)
        if agent and agent.group_id:
            return self._groups.get(agent.group_id)
        return None

    # --- Homes ---

    def place_home(self, agent_id: UUID, x: int, y: int) -> Home:
        home = Home(x=x, y=y, agent_id=agent_id)
        self._homes[agent_id] = home
        self._home_tiles.add((x, y))
        return home

    def remove_home(self, agent_id: UUID) -> Home | None:
        home = self._homes.pop(agent_id, None)
        if home:
            self._home_tiles.discard((home.x, home.y))
        return home

    def all_homes(self) -> list[Home]:
        return list(self._homes.values())

    def is_home_tile(self, x: int, y: int) -> bool:
        return (x, y) in self._home_tiles

    def find_home_tile(self, near_x: int, near_y: int, pending_regrow: set[tuple[int, int]] | None = None) -> tuple[int, int] | None:
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([(near_x, near_y)])
        visited.add((near_x, near_y))
        while queue:
            x, y = queue.popleft()
            if (
                not self.is_river_tile(x, y)
                and not self.is_home_tile(x, y)
                and self.get_food_at(x, y) is None
                and (pending_regrow is None or (x, y) not in pending_regrow)
            ):
                return (x, y)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny) and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return None

    def update_group_centers(self) -> None:
        for group in self._groups.values():
            members = [self._agents[mid] for mid in group.member_ids if mid in self._agents]
            group.update_center(members)

    def compute_food_visibility(self, agent_vision: dict) -> dict:
        group_shared_food: dict[UUID, list[Food]] = {}
        for group in self._groups.values():
            seen_ids: set[UUID] = set()
            shared: list[Food] = []
            for mid in group.member_ids:
                member = self._agents.get(mid)
                if not member:
                    continue
                for f in self.food_in_vision(member, agent_vision[mid]):
                    if f.id not in seen_ids:
                        seen_ids.add(f.id)
                        shared.append(f)
            group_shared_food[group.id] = shared

        agent_food: dict[UUID, list[Food]] = {}
        for agent in self.all_living_agents():
            group = self.group_for_agent(agent.id)
            agent_food[agent.id] = (
                group_shared_food[group.id] if group
                else self.food_in_vision(agent, agent_vision[agent.id])
            )
        return agent_food

    def prune_groups(self) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        for group in list(self._groups.values()):
            for mid in list(group.member_ids):
                member = self._agents.get(mid)
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
                self.disband_group(group.id)
                events.append(("group_disbanded", {"group_id": str(group.id)}))
        return events

    def process_agent_death(self, agent_id: UUID) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        agent = self._agents.get(agent_id)
        if agent:
            agent.die()
            if agent.group_id:
                group = self.group_for_agent(agent_id)
                if group:
                    group.member_ids.discard(agent_id)
                    if group.size < 2:
                        self.disband_group(group.id)
                        events.append(("group_disbanded", {"group_id": str(group.id)}))
            home = self.remove_home(agent_id)
            if home:
                events.append(("home_removed", {"home": home.model_dump(mode="json")}))
            events.append(("agent_died", {"agent": agent.model_dump(mode="json")}))
        return events

    def reset(self) -> None:
        self._agents.clear()
        self._food.clear()
        self._groups.clear()
        self._rivers.clear()
        self._river_tiles.clear()
        self._homes.clear()
        self._home_tiles.clear()

    # --- Rivers ---

    def add_spring(self, x: int, y: int) -> River:
        if not self.in_bounds(x, y):
            raise ValueError(f"Position ({x}, {y}) is out of bounds")
        river = River(tiles=[(x, y)])
        self._rivers[river.id] = river
        self._river_tiles.add((x, y))
        return river

    def extend_river(self, river: River, x: int, y: int) -> None:
        river.tiles.append((x, y))
        self._river_tiles.add((x, y))
        if y >= self.height - 1:
            river.complete = True

    def is_river_tile(self, x: int, y: int) -> bool:
        return (x, y) in self._river_tiles

    def all_rivers(self) -> list[River]:
        return list(self._rivers.values())


world = World(width=100, height=100)
