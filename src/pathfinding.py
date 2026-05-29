import heapq

from config import HILL_COST_SCALE
from world import World


def astar(
    world: World,
    start: tuple[int, int],
    goal: tuple[int, int],
    blocked: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    if start == goal:
        return []

    open_heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path: list[tuple[int, int]] = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        cx, cy = current
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if not world.in_bounds(nx, ny):
                continue
            neighbor = (nx, ny)
            if blocked and neighbor in blocked and neighbor != goal:
                continue
            elev_diff = world.elevation_at(nx, ny) - world.elevation_at(cx, cy)
            move_cost = 1.0 + max(0.0, elev_diff) * HILL_COST_SCALE
            tentative_g = g_score[current] + move_cost
            if tentative_g < g_score.get(neighbor, 1e9):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = abs(nx - goal[0]) + abs(ny - goal[1])
                heapq.heappush(open_heap, (tentative_g + h, neighbor))

    return []
