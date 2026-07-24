from __future__ import annotations

import random
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from config import PLANT_SHADE, PLANT_SHADE_ADJACENT
import event_bus
from events import Event
from pos import Pos

_PLANT_SPECS: dict[str, dict] = {
    "fruit_tree": {
        "max_fruit": 12,
        "base_growth_rate": 0.016,
        "germination_rate": 0.005,
        "fruit_per_tick": 0.1,
    },
}


class Plant(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    plant_type: str
    fruit_count: float
    max_fruit: int
    growth_rate: float
    fruit_per_tick: float

    @property
    def pos(self) -> Pos:
        return Pos(self.x, self.y)

    def remove(self, n: int) -> None:
        self.fruit_count = max(0.0, self.fruit_count - n)


_PLANT_TYPE, _PLANT_SPEC = next(iter(_PLANT_SPECS.items()))


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
            if rng.random() >= _PLANT_SPEC["germination_rate"]:
                continue

            plant = Plant(
                x=pos.x,
                y=pos.y,
                plant_type=_PLANT_TYPE,
                fruit_count=float(_PLANT_SPEC["max_fruit"]),
                max_fruit=_PLANT_SPEC["max_fruit"],
                growth_rate=_PLANT_SPEC["base_growth_rate"],
                fruit_per_tick=_PLANT_SPEC["fruit_per_tick"],
            )
            self._plants[plant.id] = plant
            self._by_pos[pos] = plant
            placed.append(plant)

        self.rebuild_shade_grid()
        return placed

    def grow_plants(self) -> None:
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

    def fruiting_plant_at(self, pos: Pos) -> Plant | None:
        plant = self._by_pos.get(pos)
        return plant if plant is not None and plant.fruit_count >= 1 else None

    def get_plant(self, plant_id: UUID) -> Plant | None:
        return self._plants.get(plant_id)

    def remove_fruit_at(self, pos: Pos) -> Plant | None:
        plant = self._by_pos.get(pos)
        if plant is None or plant.fruit_count < 1:
            return None
        plant.fruit_count -= 1
        if plant.fruit_count < 1:
            event_bus.publish(
                Event(
                    "fruit_depleted",
                    {"plant_id": str(plant.id), "x": plant.x, "y": plant.y},
                )
            )
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
