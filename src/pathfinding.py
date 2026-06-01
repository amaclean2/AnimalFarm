import heapq

from config import HILL_COST_SCALE, RIVER_CROSSING_COST
from pos import Pos
from world import World


def astar(
    world: World,
    start: Pos,
    goal: Pos,
    blocked: set[Pos] | None = None,
    max_radius: int | None = None,
) -> list[Pos]:
    if start == goal:
        return []

    open_heap: list[tuple[float, Pos]] = [(0.0, start)]
    came_from: dict[Pos, Pos] = {}
    g_score: dict[Pos, float] = {start: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path: list[Pos] = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for neighbor in (
            Pos(current.x + 1, current.y),
            Pos(current.x - 1, current.y),
            Pos(current.x, current.y + 1),
            Pos(current.x, current.y - 1),
        ):
            if not world.in_bounds(neighbor):
                continue
            if (
                max_radius is not None
                and abs(neighbor.x - start.x) + abs(neighbor.y - start.y) > max_radius
            ):
                continue
            if blocked and neighbor in blocked and neighbor != goal:
                continue
            elev_diff = world.elevation_at(neighbor) - world.elevation_at(current)
            move_cost = 1.0 + max(0.0, elev_diff) * HILL_COST_SCALE
            if world.rivers.is_river_tile(neighbor):
                move_cost += RIVER_CROSSING_COST
            tentative_g = g_score[current] + move_cost
            if tentative_g < g_score.get(neighbor, 1e9):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = abs(neighbor.x - goal.x) + abs(neighbor.y - goal.y)
                heapq.heappush(open_heap, (tentative_g + h, neighbor))

    return []
