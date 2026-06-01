from uuid import UUID

from agents.agent import Agent
from config import BASE_COHESION
from group import Group
from pos import Pos


class Agents:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._data: dict[UUID, Agent] = {}
        self._groups: dict[UUID, Group] = {}

    # --- Agent registry ---

    def add(self, pos: Pos, birth_tick: int = 0, age: int = 0) -> Agent:
        if not (0 <= pos.x < self._width and 0 <= pos.y < self._height):
            raise ValueError(f"Position {pos} is out of bounds")
        agent = Agent(x=pos.x, y=pos.y, birth_tick=birth_tick, age=age)
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

    def in_range(self, agent: Agent, range_val: float) -> list[Agent]:
        return [
            a
            for a in self._data.values()
            if a.alive
            and a.id != agent.id
            and abs(a.x - agent.x) + abs(a.y - agent.y) <= range_val
        ]

    def reset(self) -> None:
        self._data.clear()
        self._groups.clear()

    # --- Group management ---

    def add_group(self, member_ids: set[UUID]) -> Group:
        group = Group(member_ids=set(member_ids))
        for mid in member_ids:
            agent = self.get(mid)
            if agent:
                agent.group_id = group.id
        self._groups[group.id] = group
        return group

    def get_group(self, group_id: UUID) -> Group | None:
        return self._groups.get(group_id)

    def disband_group(self, group_id: UUID) -> Group | None:
        group = self._groups.pop(group_id, None)
        if group:
            for mid in group.member_ids:
                agent = self.get(mid)
                if agent:
                    agent.group_id = None
        return group

    @property
    def all_groups(self) -> list[Group]:
        return list(self._groups.values())

    def group_for_agent(self, agent_id: UUID) -> Group | None:
        agent = self.get(agent_id)
        if agent and agent.group_id:
            return self._groups.get(agent.group_id)
        return None

    def update_group_centers(self) -> None:
        for group in self._groups.values():
            members = [
                self.get(mid) for mid in group.member_ids if self.get(mid) is not None
            ]
            group.update_center(members)

    def form_groups(self, events: list[tuple[str, dict]]) -> None:
        for group in self.all_groups:
            members = [
                self.get(mid) for mid in group.member_ids if self.get(mid) is not None
            ]
            group.update_center(members)

        lone_agents = [a for a in self.all_living if a.group_id is None]

        for agent in lone_agents:
            if agent.group_id is not None:
                continue

            for group in self.all_groups:
                dist = abs(agent.x - group.center_x) + abs(agent.y - group.center_y)
                if dist <= group.cohesion_radius:
                    group.member_ids.add(agent.id)
                    agent.group_id = group.id
                    events.append(
                        (
                            "agent_joined_group",
                            {
                                "agent_id": str(agent.id),
                                "group_id": str(group.id),
                            },
                        )
                    )
                    break

            if agent.group_id is not None:
                continue

            for other in lone_agents:
                if other.id == agent.id or other.group_id is not None:
                    continue
                dist = abs(agent.x - other.x) + abs(agent.y - other.y)
                if dist <= BASE_COHESION:
                    group = self.add_group({agent.id, other.id})
                    group.update_center([agent, other])
                    events.append(
                        (
                            "group_formed",
                            {
                                "group_id": str(group.id),
                                "member_ids": [str(agent.id), str(other.id)],
                            },
                        )
                    )
                    break

    def prune_groups(self) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        for group in list(self._groups.values()):
            for mid in list(group.member_ids):
                member = self.get(mid)
                if member is None:
                    group.member_ids.discard(mid)
                    continue
                dist = abs(member.x - group.center_x) + abs(member.y - group.center_y)
                if dist > group.attraction_range:
                    group.member_ids.discard(mid)
                    member.group_id = None
                    events.append(
                        (
                            "agent_left_group",
                            {
                                "agent_id": str(mid),
                                "group_id": str(group.id),
                            },
                        )
                    )
            if group.size < 2:
                self.disband_group(group.id)
                events.append(("group_disbanded", {"group_id": str(group.id)}))
        return events

    def process_agent_death(self, agent_id: UUID) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        agent = self.get(agent_id)
        if agent:
            agent.die()
            if agent.group_id:
                group = self.group_for_agent(agent_id)
                if group:
                    group.member_ids.discard(agent_id)
                    if group.size < 2:
                        self.disband_group(group.id)
                        events.append(("group_disbanded", {"group_id": str(group.id)}))
            events.append(("agent_died", {"agent": agent.model_dump(mode="json")}))
        return events
