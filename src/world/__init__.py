from __future__ import annotations

import math
import random
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent import Agent

from config import (
    REST_FOOD_WEIGHT,
    REST_NOISE_WEIGHT,
    REST_RIVER_WEIGHT,
    REST_SPOT_SEEK_THRESHOLD,
    RIVER_DIRECTION_BIAS,
    RIVER_GRAVITY_SCALE,
    RIVER_POOL_RISE_RATE,
)
from noise import value_noise_2d
from pos import Pos
from .river import River, Rivers
from .weather import WeatherSystem

_DIRECTIONS = [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]


class World:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.rivers = Rivers(width, height)
        self._rest_quality: dict[Pos, float] = {}
        self._elevation: list[float] = []
        self.weather = WeatherSystem(width, height)

    def in_bounds(self, pos: Pos) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def valid_moves(self, pos: Pos) -> list[Pos]:
        return [
            Pos(pos.x + dx, pos.y + dy)
            for dx, dy in _DIRECTIONS
            if self.in_bounds(Pos(pos.x + dx, pos.y + dy))
        ]

    # --- Rest quality ---

    def generate_rest_quality(self, food_positions: list[Pos], seed: int) -> None:
        river_dist = self._distance_transform(self.rivers.all_tiles)
        food_dist = (
            self._distance_transform(set(food_positions)) if food_positions else {}
        )

        max_river_dist = max(river_dist.values(), default=1)
        max_food_dist = max(food_dist.values(), default=1)

        for x in range(self.width):
            for y in range(self.height):
                p = Pos(x, y)

                if self.rivers.is_river_tile(p):
                    self._rest_quality[p] = 0.0
                    continue

                coarse = value_noise_2d(x, y, scale=20.0, seed=seed)
                fine = value_noise_2d(x, y, scale=8.0, seed=seed + 999)
                noise = 0.7 * coarse + 0.3 * fine

                rd = river_dist.get(p, max_river_dist)
                river_bonus = 1.0 - rd / max_river_dist

                fd = food_dist.get(p, max_food_dist)
                food_bonus = 1.0 - fd / max_food_dist

                quality = (
                    REST_NOISE_WEIGHT * noise
                    + REST_RIVER_WEIGHT * river_bonus
                    + REST_FOOD_WEIGHT * food_bonus
                )
                self._rest_quality[p] = max(0.0, min(1.0, quality))

    def rest_quality_at(self, pos: Pos) -> float:
        return self._rest_quality.get(pos, 0.0)

    def best_rest_in_vision(
        self,
        agent: Agent,
        vision: float,
        sleeping_tiles: set[Pos] | None = None,
    ) -> Pos | None:
        best_pos: Pos | None = None
        best_quality = REST_SPOT_SEEK_THRESHOLD

        for dx in range(-int(vision), int(vision) + 1):
            for dy in range(-int(vision), int(vision) + 1):
                if abs(dx) + abs(dy) > vision:
                    continue
                t = Pos(agent.x + dx, agent.y + dy)
                if not self.in_bounds(t):
                    continue
                if self.rivers.is_river_tile(t):
                    continue
                if sleeping_tiles and t in sleeping_tiles:
                    continue
                quality = self._rest_quality.get(t, 0.0)

                if quality > best_quality:
                    best_quality = quality
                    best_pos = t

        return best_pos

    def _distance_transform(self, sources: set[Pos]) -> dict[Pos, int]:
        dist: dict[Pos, int] = {}
        queue: deque[Pos] = deque()
        for pos in sources:
            dist[pos] = 0
            queue.append(pos)
        while queue:
            p = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                n = Pos(p.x + dx, p.y + dy)
                if self.in_bounds(n) and n not in dist:
                    dist[n] = dist[p] + 1
                    queue.append(n)
        return dist

    # --- Elevation ---

    def generate_elevation(self, seed: int, coarse_scale: float = 90.0) -> None:
        self._elevation = []
        for y in range(self.height):
            for x in range(self.width):
                coarse = value_noise_2d(x, y, scale=coarse_scale, seed=seed)
                coarse = max(0.0, min(1.0, (coarse - 0.5) * 1.3 + 0.5))
                fine = value_noise_2d(x, y, scale=3.0, seed=seed + 2)
                self._elevation.append(0.925 * coarse + 0.075 * fine)

    def elevation_at(self, pos: Pos) -> float:
        if not self._elevation:
            return 0.0
        return self._elevation[pos.y * self.width + pos.x]

    def all_elevation(self) -> list[float]:
        return self._elevation

    # --- Rivers ---

    def _river_extend(
        self,
        river: River,
        pos: Pos,
        events: list[tuple[str, dict]],
        food=None,
    ) -> None:
        self.rivers.extend(river, pos)

        if food is not None:
            removed_food = food.remove_food_at(pos)

            if removed_food:
                events.append(
                    (
                        "food_drowned",
                        {"food_id": str(removed_food.id), "x": pos.x, "y": pos.y},
                    )
                )

        events.append(
            ("river_tile_added", {"river_id": str(river.id), "x": pos.x, "y": pos.y})
        )

        if river.complete:
            events.append(
                ("river_completed", {"river_id": str(river.id), "reached_bottom": True})
            )

    def flow_rivers(self, events: list[tuple[str, dict]], food=None) -> None:
        for river in self.rivers.all_rivers:

            if river.complete:
                continue

            head = river.head
            if head is None:
                continue

            hx, hy = head
            elev_head = self.elevation_at(head)

            candidates = []
            for dx, dy in [(0, 1), (-1, 0), (1, 0), (0, -1)]:
                n = Pos(hx + dx, hy + dy)
                if self.in_bounds(n) and not self.rivers.is_river_tile(n):
                    candidates.append(n)

            if not candidates:
                river.complete = True
                events.append(
                    (
                        "river_completed",
                        {"river_id": str(river.id), "reached_bottom": False},
                    )
                )
                continue

            weights = []
            for n in candidates:
                delta = elev_head - self.elevation_at(n)
                same_dir = n.x - hx == river.last_dx and n.y - hy == river.last_dy
                dir_bonus = RIVER_DIRECTION_BIAS if same_dir else 0.0
                weights.append(
                    max(0.05, math.exp((delta + dir_bonus) * RIVER_GRAVITY_SCALE))
                )

            chosen = random.choices(candidates, weights=weights, k=1)[0]
            chosen_elev = self.elevation_at(chosen)

            if chosen_elev <= elev_head:
                river.pool_level = 0.0
                river.last_dx, river.last_dy = chosen.x - hx, chosen.y - hy
                self._river_extend(river, chosen, events, food)
            else:
                wall_height = chosen_elev - elev_head
                river.pool_level += RIVER_POOL_RISE_RATE

                if river.pool_level >= wall_height:
                    river.pool_level = 0.0
                    river.last_dx, river.last_dy = chosen.x - hx, chosen.y - hy
                    self._river_extend(river, chosen, events, food)

    def reset(self) -> None:
        self.rivers.clear()
        self._rest_quality.clear()
        self._elevation.clear()
        self.weather.reset()
