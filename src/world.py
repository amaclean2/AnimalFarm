import json
from collections import deque
from uuid import UUID

from agent import Agent
from config import (
    LOGS_DIR,
    REST_NOISE_WEIGHT,
    REST_RIVER_WEIGHT,
    REST_FOOD_WEIGHT,
    REST_SPOT_SEEK_THRESHOLD,
)
from food import Food
from group import Group
from noise import value_noise_2d
from river import River
from weather import WeatherSystem

_DIRECTIONS = [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]


def _write_decision_log(agent: Agent) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    short_id = str(agent.id)[:8]
    path = LOGS_DIR / f"agent_{short_id}_decisions.json"
    data = {
        "agent_id": str(agent.id),
        "mutations": agent.mutations,
        "age_at_death": agent.age,
        "birth_tick": agent.birth_tick,
        "total_decisions": len(agent.decision_log),
        "decisions": agent.decision_log,
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class World:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._agents: dict[UUID, Agent] = {}
        self._food: dict[tuple[int, int], Food] = {}
        self._groups: dict[UUID, Group] = {}
        self._rivers: dict[UUID, River] = {}
        self._river_tiles: set[tuple[int, int]] = set()
        self._rest_quality: dict[tuple[int, int], float] = {}
        self._elevation: list[float] = []
        self._weather = WeatherSystem(width, height)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def valid_moves(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            (x + dx, y + dy) for dx, dy in _DIRECTIONS if self.in_bounds(x + dx, y + dy)
        ]

    def food_in_vision(
        self, agent: Agent, vision_range: float | None = None
    ) -> list[Food]:
        r = vision_range if vision_range is not None else agent.vision_range
        return [
            f
            for f in self._food.values()
            if abs(f.x - agent.x) + abs(f.y - agent.y) <= r
        ]

    def agents_in_range(self, agent: Agent, range_val: float) -> list[Agent]:
        return [
            a
            for a in self._agents.values()
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

    # --- Rest quality ---

    def generate_rest_quality(
        self, food_positions: list[tuple[int, int]], seed: int
    ) -> None:
        river_dist = self._distance_transform(self._river_tiles)
        food_dist = (
            self._distance_transform(set(food_positions)) if food_positions else {}
        )

        max_river_dist = max(river_dist.values(), default=1)
        max_food_dist = max(food_dist.values(), default=1)

        for x in range(self.width):
            for y in range(self.height):
                if self.is_river_tile(x, y):
                    self._rest_quality[(x, y)] = 0.0
                    continue

                coarse = value_noise_2d(x, y, scale=20.0, seed=seed)
                fine = value_noise_2d(x, y, scale=8.0, seed=seed + 999)
                noise = 0.7 * coarse + 0.3 * fine

                rd = river_dist.get((x, y), max_river_dist)
                river_bonus = 1.0 - rd / max_river_dist

                fd = food_dist.get((x, y), max_food_dist)
                food_bonus = 1.0 - fd / max_food_dist

                quality = (
                    REST_NOISE_WEIGHT * noise
                    + REST_RIVER_WEIGHT * river_bonus
                    + REST_FOOD_WEIGHT * food_bonus
                )
                self._rest_quality[(x, y)] = max(0.0, min(1.0, quality))

    def rest_quality_at(self, x: int, y: int) -> float:
        return self._rest_quality.get((x, y), 0.0)

    def best_rest_in_vision(
        self,
        agent: Agent,
        vision: float,
        sleeping_tiles: set[tuple[int, int]] | None = None,
    ) -> tuple[int, int] | None:
        best_pos: tuple[int, int] | None = None
        best_quality = REST_SPOT_SEEK_THRESHOLD

        for dx in range(-int(vision), int(vision) + 1):
            for dy in range(-int(vision), int(vision) + 1):
                if abs(dx) + abs(dy) > vision:
                    continue
                tx, ty = agent.x + dx, agent.y + dy
                if not self.in_bounds(tx, ty):
                    continue
                if self.is_river_tile(tx, ty):
                    continue
                if sleeping_tiles and (tx, ty) in sleeping_tiles:
                    continue
                quality = self._rest_quality.get((tx, ty), 0.0)

                if quality > best_quality:
                    best_quality = quality
                    best_pos = (tx, ty)

        return best_pos

    def _distance_transform(
        self, sources: set[tuple[int, int]]
    ) -> dict[tuple[int, int], int]:
        dist: dict[tuple[int, int], int] = {}
        queue: deque[tuple[int, int]] = deque()
        for pos in sources:
            dist[pos] = 0
            queue.append(pos)
        while queue:
            x, y = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny) and (nx, ny) not in dist:
                    dist[(nx, ny)] = dist[(x, y)] + 1
                    queue.append((nx, ny))
        return dist

    def update_group_centers(self) -> None:
        for group in self._groups.values():
            members = [
                self._agents[mid] for mid in group.member_ids if mid in self._agents
            ]
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
                group_shared_food[group.id]
                if group
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
                    events.append(
                        (
                            "agent_left_group",
                            {
                                "agent_id": str(mid),
                                "group_id": str(group.id),
                            },
                        )
                    )
            if group.size < 2:
                self.disband_group(group.id)
                events.append(("group_disbanded", {"group_id": str(group.id)}))
        return events

    def process_agent_death(self, agent_id: UUID) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        agent = self._agents.get(agent_id)
        if agent:
            if agent.decision_log:
                _write_decision_log(agent)
            agent.die()
            if agent.group_id:
                group = self.group_for_agent(agent_id)
                if group:
                    group.member_ids.discard(agent_id)
                    if group.size < 2:
                        self.disband_group(group.id)
                        events.append(("group_disbanded", {"group_id": str(group.id)}))
            events.append(("agent_died", {"agent": agent.model_dump(mode="json")}))
        return events

    def generate_elevation(self, seed: int) -> None:
        self._elevation = []
        for y in range(self.height):
            for x in range(self.width):
                coarse = value_noise_2d(x, y, scale=40.0, seed=seed)
                medium = value_noise_2d(x, y, scale=15.0, seed=seed + 1)
                fine = value_noise_2d(x, y, scale=6.0, seed=seed + 2)
                self._elevation.append(0.4 * coarse + 0.3 * medium + 0.3 * fine)

    def elevation_at(self, x: int, y: int) -> float:
        if not self._elevation:
            return 0.0
        return self._elevation[y * self.width + x]

    def all_elevation(self) -> list[float]:
        return self._elevation

    def generate_climate(self, seed: int) -> None:
        self._weather.generate(seed, self.elevation_at)

    def temperature_at(self, x: int, y: int) -> float:
        return self._weather.temperature_at(x, y)

    def precipitation_at(self, x: int, y: int) -> float:
        return self._weather.precipitation_at(x, y)

    def all_temperature(self) -> list[float]:
        return self._weather.base_temperature()

    def all_precipitation(self) -> list[float]:
        return self._weather.base_precipitation()

    def tick_clouds(self) -> None:
        self._weather.tick()

    def clouds_to_list(self) -> list[dict]:
        return self._weather.clouds_to_list()

    def reset(self) -> None:
        self._agents.clear()
        self._food.clear()
        self._groups.clear()
        self._rivers.clear()
        self._river_tiles.clear()
        self._rest_quality.clear()
        self._elevation.clear()
        self._weather.reset()

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
        if x == 0 or x >= self.width - 1 or y == 0 or y >= self.height - 1:
            river.complete = True

    def is_river_tile(self, x: int, y: int) -> bool:
        return (x, y) in self._river_tiles

    def all_rivers(self) -> list[River]:
        return list(self._rivers.values())

    def all_river_tiles(self) -> set[tuple[int, int]]:
        return self._river_tiles


world = World(width=100, height=100)
