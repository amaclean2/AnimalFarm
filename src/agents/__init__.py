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

    # --- Agent registry ---

    def add(self, pos: Pos, birth_tick: int = 0, age: int = 0) -> Agent:
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

    def find_mate_target(self, agent: Agent, vision: float, tick: int) -> Pos | None:
        if not agent.is_eligible_to_mate(tick):
            return None
        best: Pos | None = None
        best_dist = float("inf")
        for other in self.in_range(agent, vision):
            if not other.is_eligible_to_mate(tick):
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

    def reset(self) -> None:
        self._data.clear()
        self._grid.clear()

    def process_agent_death(self, agent_id: UUID) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        agent = self.get(agent_id)
        if agent:
            agent.die()
            events.append(("agent_died", {"agent": agent.model_dump(mode="json")}))
        return events
