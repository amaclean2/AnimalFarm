import random

from food import Food
from group import BASE_COHESION
from world import World

FOOD_REGROW_TICKS = 40

FOOD_SPREAD_SIGMA = 20.0
FOOD_SPREAD_CANDIDATES = 50
FOOD_WATER_WEIGHT = 2.0
FOOD_CLUSTER_WEIGHT = 1.0
FOOD_SCORE_FLOOR = 0.01

RIVER_DOWN_WEIGHT = 3.0
RIVER_LATERAL_WEIGHT = 2.0
RIVER_UP_WEIGHT = 0.5


def form_groups(world: World, events: list[tuple[str, dict]]) -> None:
    for group in world.all_groups():
        members = [
            world.get_agent(mid)
            for mid in group.member_ids
            if world.get_agent(mid) is not None
        ]
        group.update_center(members)

    lone_agents = [a for a in world.all_living_agents() if a.group_id is None]

    for agent in lone_agents:
        if agent.group_id is not None:
            continue

        for group in world.all_groups():
            dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
            if dist <= group.cohesion_radius:
                group.member_ids.add(agent.id)
                agent.group_id = group.id
                events.append(("agent_joined_group", {
                    "agent_id": str(agent.id),
                    "group_id": str(group.id),
                }))
                break

        if agent.group_id is not None:
            continue

        for other in lone_agents:
            if other.id == agent.id or other.group_id is not None:
                continue
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            if dist <= BASE_COHESION:
                group = world.add_group({agent.id, other.id})
                group.update_center([agent, other])
                group.home = (round(group.center_x), round(group.center_y))
                events.append(("group_formed", {
                    "group_id": str(group.id),
                    "member_ids": [str(agent.id), str(other.id)],
                    "home": list(group.home) if group.home else None,
                }))
                break


def spawn_food_near(
    world: World, anchor_x: int, anchor_y: int, events: list[tuple[str, dict]]
) -> None:
    river_tiles = list(world._river_tiles)
    food_list = world.all_food()

    candidates: list[tuple[int, int]] = []
    for _ in range(FOOD_SPREAD_CANDIDATES):
        cx = int(random.gauss(anchor_x, FOOD_SPREAD_SIGMA))
        cy = int(random.gauss(anchor_y, FOOD_SPREAD_SIGMA))
        if not world.in_bounds(cx, cy):
            continue
        if world.is_river_tile(cx, cy):
            continue
        if world.get_food_at(cx, cy) is not None:
            continue
        candidates.append((cx, cy))

    if not candidates:
        return

    weights: list[float] = []
    for cx, cy in candidates:
        if river_tiles:
            water_dist = min(abs(cx - rx) + abs(cy - ry) for rx, ry in river_tiles)
            water_score = FOOD_WATER_WEIGHT / (1 + water_dist)
        else:
            water_score = 0.0

        if food_list:
            cluster_dist = min(abs(cx - f.x) + abs(cy - f.y) for f in food_list)
            cluster_score = FOOD_CLUSTER_WEIGHT / (1 + cluster_dist)
        else:
            cluster_score = 0.0

        weights.append(water_score + cluster_score + FOOD_SCORE_FLOOR)

    chosen = random.choices(candidates, weights=weights, k=1)[0]
    food = Food(x=chosen[0], y=chosen[1])
    world._food[chosen] = food
    events.append(("food_grew", {"food": food.model_dump(mode="json")}))


def flow_rivers(world: World, events: list[tuple[str, dict]]) -> None:
    for river in world.all_rivers():
        if river.complete:
            continue
        head = river.head
        if head is None:
            continue
        hx, hy = head

        candidates: list[tuple[int, int]] = []
        weights: list[float] = []
        for dx, dy in [(0, 1), (-1, 0), (1, 0), (0, -1)]:
            nx, ny = hx + dx, hy + dy
            if not world.in_bounds(nx, ny):
                continue
            if world.is_river_tile(nx, ny):
                continue
            if dy == 1:
                w = RIVER_DOWN_WEIGHT
            elif dy == -1:
                w = RIVER_UP_WEIGHT
            else:
                w = RIVER_LATERAL_WEIGHT
            candidates.append((nx, ny))
            weights.append(w)

        if not candidates:
            river.complete = True
            events.append(("river_completed", {"river_id": str(river.id), "reached_bottom": False}))
            continue

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        world.extend_river(river, chosen[0], chosen[1])
        food = world.consume_food_at(chosen[0], chosen[1])
        if food:
            events.append(("food_drowned", {"food_id": str(food.id), "x": chosen[0], "y": chosen[1]}))
        events.append(("river_tile_added", {
            "river_id": str(river.id),
            "x": chosen[0],
            "y": chosen[1],
        }))
        if river.complete:
            events.append(("river_completed", {"river_id": str(river.id), "reached_bottom": True}))
