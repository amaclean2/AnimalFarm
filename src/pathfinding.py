import heapq

from world import World


def astar(world: World, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    if start == goal:
        return []

    open_heap: list[tuple[int, tuple[int, int]]] = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start: 0}

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
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, 10**9):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = abs(nx - goal[0]) + abs(ny - goal[1])
                heapq.heappush(open_heap, (tentative_g + h, neighbor))

    return []
