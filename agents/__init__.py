from uuid import UUID

from agents.agent import Agent
import config as _cfg
from pos import Pos

_GRID_BUCKET = 5


class Agents:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._data: dict[UUID, Agent] = {}
        self._grid: dict[tuple[int, int], list[Agent]] = {}

    def create(self, pos: Pos, birth_tick: int = 0, age: int = 0) -> Agent:

        if not (0 <= pos.x < self._width and 0 <= pos.y < self._height):
            raise ValueError(f"Position {pos} is out of bounds")

        agent = Agent(x=pos.x, y=pos.y, birth_tick=birth_tick, age=age)
        agent.next_decision_tick = agent.id.int % _cfg.DECISION_STRIDE
        self._data[agent.id] = agent
        return agent

    def get(self, agent_id: UUID) -> Agent | None:
        return self._data.get(agent_id)

    def remove(self, agent_id: UUID) -> Agent | None:
        return self._data.pop(agent_id, None)

    def all(self) -> list[Agent]:
        return list(self._data.values())

    @property
    def all_living(self) -> list[Agent]:
        return [a for a in self._data.values() if a.alive]

    def find_mate_target(self, agent: Agent, tick_count: int) -> Pos | None:

        if not agent.is_eligible_to_mate(tick_count):
            return None

        best: Pos | None = None
        best_dist = float("inf")

        for other in self.in_range(agent, agent.vision_range):

            if not other.is_eligible_to_mate(tick_count):
                continue

            dist = abs(agent.x - other.x) + abs(agent.y - other.y)

            if dist < best_dist:
                best_dist = dist
                best = other.pos

        return best

    def build_spatial_grid(self) -> None:
        self._grid = {}

        for a in self._data.values():

            if a.alive:
                key = (a.x // _GRID_BUCKET, a.y // _GRID_BUCKET)
                self._grid.setdefault(key, []).append(a)

    def count_agents_near(
        self, pos: Pos, range_val: float, exclude_id: UUID | None = None
    ) -> int:
        if not self._grid:
            return sum(
                1
                for other in self._data.values()
                if other.alive
                and other.id != exclude_id
                and abs(other.x - pos.x) + abs(other.y - pos.y) <= range_val
            )

        radius = int(range_val)
        bucket_x0 = (pos.x - radius) // _GRID_BUCKET - 1
        bucket_x1 = (pos.x + radius) // _GRID_BUCKET + 1
        bucket_y0 = (pos.y - radius) // _GRID_BUCKET - 1
        bucket_y1 = (pos.y + radius) // _GRID_BUCKET + 1
        count = 0

        for bucket_x in range(bucket_x0, bucket_x1 + 1):
            for bucket_y in range(bucket_y0, bucket_y1 + 1):
                for other in self._grid.get((bucket_x, bucket_y), []):
                    if (
                        other.id != exclude_id
                        and abs(other.x - pos.x) + abs(other.y - pos.y) <= range_val
                    ):
                        count += 1

        return count

    def in_range(self, agent: Agent, range_val: float) -> list[Agent]:
        if not self._grid:
            return [
                a
                for a in self._data.values()
                if a.alive
                and a.id != agent.id
                and abs(a.x - agent.x) + abs(a.y - agent.y) <= range_val
            ]

        r = int(range_val)
        bx0 = (agent.x - r) // _GRID_BUCKET - 1
        bx1 = (agent.x + r) // _GRID_BUCKET + 1
        by0 = (agent.y - r) // _GRID_BUCKET - 1
        by1 = (agent.y + r) // _GRID_BUCKET + 1
        result = []

        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                for a in self._grid.get((bx, by), []):
                    if (
                        a.id != agent.id
                        and abs(a.x - agent.x) + abs(a.y - agent.y) <= range_val
                    ):
                        result.append(a)

        return result

    def reproduce(self, world, tick_count: int) -> int:
        from agents.reproduction import reproduce as _fn

        return _fn(world, self, tick_count)

    def reset(self) -> None:
        self._data.clear()
        self._grid.clear()
