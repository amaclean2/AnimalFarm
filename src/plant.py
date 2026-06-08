from __future__ import annotations

import random
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

import config as cfg
from config import PLANT_SHADE, PLANT_SHADE_ADJACENT
import event_bus
from events import Event
from pos import Pos

# ── Plant type specifications ─────────────────────────────────────────────────

_TEMP_FALLOFF = 7.5  # °C outside range before suitability → 0
_PRECIP_FALLOFF = 0.15
_MIN_SUITABILITY = 0.1
_RIVER_MIN_PROXIMITY = 1.0 / (1 + 6)  # river must be within 6 tiles

_PLANT_SPECS: dict[str, dict] = {
    "date_palm": {
        "temp_lo": 23.0,
        "temp_hi": 40.0,
        "precip_lo": 0.0,
        "precip_hi": 0.25,
        "requires_river": False,
        "max_fruit": 8,
        "base_growth_rate": 0.01,
        "germination_rate": 0.001,
    },
    "wild_plum": {
        "temp_lo": 0.0,
        "temp_hi": 35.0,
        "precip_lo": 0.0,
        "precip_hi": 1.0,
        "requires_river": True,
        "max_fruit": 20,
        "base_growth_rate": 0.06,
        "germination_rate": 0.02,
    },
    "fig_tree": {
        "temp_lo": 18.0,
        "temp_hi": 40.0,
        "precip_lo": 0.60,
        "precip_hi": 1.0,
        "requires_river": False,
        "max_fruit": 14,
        "base_growth_rate": 0.04,
        "germination_rate": 0.01,
    },
    "berry_bush": {
        "temp_lo": 5.0,
        "temp_hi": 25.0,
        "precip_lo": 0.30,
        "precip_hi": 0.65,
        "requires_river": False,
        "max_fruit": 10,
        "base_growth_rate": 0.03,
        "germination_rate": 0.01,
    },
    "bilberry": {
        "temp_lo": -10.0,
        "temp_hi": 10.0,
        "precip_lo": 0.20,
        "precip_hi": 0.60,
        "requires_river": False,
        "max_fruit": 6,
        "base_growth_rate": 0.02,
        "germination_rate": 0.005,
    },
}


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class ClimateData:
    temperature: float
    precipitation: float
    elevation: float
    river_proximity: float


class Plant(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    plant_type: str
    fruit_count: float
    max_fruit: int
    growth_rate: float

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)

    @property
    def ticks_per_fruit(self) -> int:
        return cfg.HARVEST_COST.get(self.plant_type, 2)

    def remove(self, n: int) -> None:
        self.fruit_count = max(0.0, self.fruit_count - n)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _range_score(value: float, lo: float, hi: float, falloff: float) -> float:
    if lo <= value <= hi:
        return 1.0

    if value < lo:
        return max(0.0, 1.0 - (lo - value) / falloff)

    return max(0.0, 1.0 - (value - hi) / falloff)


def _suitability(spec: dict, climate: ClimateData) -> float:
    if spec["requires_river"] and climate.river_proximity < _RIVER_MIN_PROXIMITY:
        return 0.0

    temp_score = _range_score(
        climate.temperature, spec["temp_lo"], spec["temp_hi"], _TEMP_FALLOFF
    )
    precip_score = _range_score(
        climate.precipitation, spec["precip_lo"], spec["precip_hi"], _PRECIP_FALLOFF
    )
    return temp_score * precip_score


# ── VegetationManager ─────────────────────────────────────────────────────────


class VegetationManager:
    def __init__(self, world) -> None:
        self._world = world
        self._plants: dict[UUID, Plant] = {}
        self._by_pos: dict[Pos, Plant] = {}
        self.shade_grid: list[float] = []
        self._visible: dict[UUID, list[Plant]] = {}

    def place_plants(self, seed: int) -> list[Plant]:
        rng = random.Random(seed)
        all_non_river: list[Pos] = [
            Pos(x, y)
            for x in range(self._world.width)
            for y in range(self._world.height)
            if not self._world.rivers.is_river_tile(Pos(x, y))
        ]
        rng.shuffle(all_non_river)

        placed: list[Plant] = []

        for pos in all_non_river:
            climate = self._world.get_climate_at(pos.x, pos.y)
            candidates: list[tuple[float, str, dict]] = []

            for ptype, spec in _PLANT_SPECS.items():
                suit = _suitability(spec, climate)
                if suit < _MIN_SUITABILITY:
                    continue
                if rng.random() < spec["germination_rate"] * suit:
                    candidates.append((suit, ptype, spec))

            if not candidates:
                continue

            suit, ptype, spec = max(candidates, key=lambda c: c[0])
            plant = Plant(
                x=pos.x,
                y=pos.y,
                plant_type=ptype,
                fruit_count=float(spec["max_fruit"]),
                max_fruit=spec["max_fruit"],
                growth_rate=spec["base_growth_rate"] * suit,
            )
            self._plants[plant.id] = plant
            self._by_pos[pos] = plant
            placed.append(plant)

        self.rebuild_shade_grid()
        return placed

    def grow_plants(self, tick: int) -> None:
        updates: list[dict] = []
        for plant in self._plants.values():
            if plant.fruit_count >= plant.max_fruit:
                continue
            old_floor = int(plant.fruit_count)
            plant.fruit_count = min(
                plant.max_fruit, plant.fruit_count + plant.growth_rate
            )
            if int(plant.fruit_count) != old_floor:
                updates.append(
                    {"plant_id": str(plant.id), "fruit_count": plant.fruit_count}
                )

        if updates:
            event_bus.publish(Event("fruit_grew", {"updates": updates}))

    def rebuild_shade_grid(self) -> None:
        w = self._world.width
        h = self._world.height
        grid = [0.0] * (w * h)

        for y in range(h):
            for x in range(w):
                pos = Pos(x, y)

                if pos in self._by_pos:
                    grid[y * w + x] = PLANT_SHADE
                    continue

                for dx, dy in (
                    (-1, 0),
                    (1, 0),
                    (0, -1),
                    (0, 1),
                    (-1, -1),
                    (-1, 1),
                    (1, -1),
                    (1, 1),
                ):
                    if self._by_pos.get(Pos(x + dx, y + dy)):
                        grid[y * w + x] = PLANT_SHADE_ADJACENT
                        break

        self.shade_grid = grid

    def shade_at(self, pos: Pos) -> float:
        if not self.shade_grid:
            return 0.0
        x, y = pos
        return self.shade_grid[y * self._world.width + x]

    def get_plant_at(self, pos: Pos) -> Plant | None:
        return self._by_pos.get(pos)

    def fruiting_plant_at(self, pos: Pos) -> Plant | None:
        plant = self._by_pos.get(pos)
        return plant if plant is not None and plant.fruit_count >= 1 else None

    def get_plant(self, plant_id: UUID) -> Plant | None:
        return self._plants.get(plant_id)

    def consume_fruit_at(self, pos: Pos) -> Plant | None:
        plant = self._by_pos.get(pos)
        if plant is None or plant.fruit_count < 1:
            return None
        plant.fruit_count -= 1
        return plant

    def nearby(self, pos: Pos, radius: float) -> list[Plant]:
        return [
            p
            for p in self._plants.values()
            if abs(p.x - pos.x) + abs(p.y - pos.y) <= radius and p.fruit_count >= 1
        ]

    def plants_in_vision(self, agent, vision_range: float | None = None) -> list[Plant]:
        r = vision_range if vision_range is not None else agent.vision_range
        return self.nearby(agent.pos, r)

    def compute_plant_visibility(self, agents) -> None:
        self._visible = {
            agent.id: self.plants_in_vision(agent) for agent in agents.all_living
        }

    def visible_for(self, agent_id: UUID) -> list[Plant]:
        return self._visible.get(agent_id, [])

    def nearby_in_vision(self, agent_id: UUID, pos: Pos, radius: float) -> list[Plant]:
        return [
            p
            for p in self._visible.get(agent_id, [])
            if abs(p.x - pos.x) + abs(p.y - pos.y) <= radius
        ]

    @property
    def all_plants(self) -> list[Plant]:
        return list(self._plants.values())

    def reset(self) -> None:
        self._plants.clear()
        self._by_pos.clear()
        self.shade_grid = []
