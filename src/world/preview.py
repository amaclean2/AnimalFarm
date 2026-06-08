import random

import config as cfg

from plant import VegetationManager
from pos import Pos
from world import World


def build_preview(
    seed: int,
    num_springs: int,
    elevation_coarse_scale: float,
) -> dict:
    preview = World(100, 100)
    preview.generate_elevation(seed=seed, coarse_scale=elevation_coarse_scale)
    preview.weather.generate(seed, lambda x, y: preview.elevation_at(Pos(x, y)))

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    peaks = [
        Pos(x, y)
        for x in range(1, preview.width - 1)
        for y in range(1, preview.height - 1)
        if all(
            preview.elevation_at(Pos(x, y)) > preview.elevation_at(Pos(x + dx, y + dy))
            for dx, dy in neighbors
        )
    ]

    if len(peaks) < num_springs:
        peaks = sorted(
            [Pos(x, y) for x in range(preview.width) for y in range(preview.height)],
            key=lambda p: preview.elevation_at(p),
            reverse=True,
        )

    chosen_springs = random.sample(peaks, min(num_springs, len(peaks)))
    for pos in chosen_springs:
        preview.rivers.add_spring(pos)
    while not all(r.complete for r in preview.rivers.all_rivers):
        preview.flow_rivers()

    preview.generate_river_proximity()
    vegetation = VegetationManager(preview)
    plants_placed = vegetation.place_plants(seed)

    return {
        "width": preview.width,
        "height": preview.height,
        "seed": seed,
        "elevation": preview.all_elevation(),
        "rivers": [
            {"river_id": str(r.id), "tiles": [list(t) for t in r.tiles]}
            for r in preview.rivers.all_rivers
        ],
        "plants": [
            {"x": p.x, "y": p.y, "plant_type": p.plant_type} for p in plants_placed
        ],
        "clouds": preview.weather.clouds_to_list(),
    }
