import math
import random

import config as cfg

from food import FoodManager
from pos import Pos
from world import World


def build_preview(
    seed: int,
    num_springs: int,
    num_food_clusters: int,
    food_peak_probability: float,
    elevation_coarse_scale: float,
) -> dict:
    preview = World(100, 100)
    food = FoodManager(preview)
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
        preview.flow_rivers([])

    river_tiles = list(preview.rivers.all_tiles)
    centers = random.sample(river_tiles, min(num_food_clusters, len(river_tiles)))

    food_placed = []

    for x in range(preview.width):
        for y in range(preview.height):
            if preview.rivers.is_river_tile(Pos(x, y)):
                continue
            nearest_d2 = min((x - c.x) ** 2 + (y - c.y) ** 2 for c in centers)
            prob = food_peak_probability * math.exp(
                -nearest_d2 / (2 * cfg.CLUSTER_SIGMA**2)
            )

            if random.random() < prob:
                food.place_food(Pos(x, y))
                food_placed.append({"x": x, "y": y})

    return {
        "width": preview.width,
        "height": preview.height,
        "seed": seed,
        "elevation": preview.all_elevation(),
        "rivers": [
            {"river_id": str(r.id), "tiles": [list(t) for t in r.tiles]}
            for r in preview.rivers.all_rivers
        ],
        "food": food_placed,
        "clouds": preview.weather.clouds_to_list(),
    }
