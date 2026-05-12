from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from world import world

router = APIRouter()


class AgentStats(BaseModel):
    id: UUID
    x: int
    y: int
    health: int
    age: int
    group_id: UUID | None
    alive: bool
    birth_tick: int


class GroupStats(BaseModel):
    id: UUID
    size: int
    gravity: float
    cohesion_radius: float
    attraction_range: float
    center_x: float
    center_y: float
    member_ids: list[UUID]


class WorldStats(BaseModel):
    agent_count: int
    group_count: int
    food_count: int
    mutation_counts: dict[str, int]
    agents: list[AgentStats]
    groups: list[GroupStats]


@router.get("/stats", response_model=WorldStats)
async def get_stats() -> WorldStats:
    all_agents = world.all_agents()

    agents = [
        AgentStats(
            id=a.id,
            x=a.x,
            y=a.y,
            health=a.health,
            age=a.age,
            group_id=a.group_id,
            alive=a.alive,
            birth_tick=a.birth_tick,
        )
        for a in all_agents
    ]

    mutation_counts: dict[str, int] = {}
    for a in all_agents:
        for m in a.mutations:
            mutation_counts[m] = mutation_counts.get(m, 0) + 1

    groups = [
        GroupStats(
            id=g.id,
            size=g.size,
            gravity=round(g.gravity, 3),
            cohesion_radius=round(g.cohesion_radius, 3),
            attraction_range=round(g.attraction_range, 3),
            center_x=round(g.center_x, 2),
            center_y=round(g.center_y, 2),
            member_ids=list(g.member_ids),
        )
        for g in world.all_groups()
    ]

    return WorldStats(
        agent_count=len(agents),
        group_count=len(groups),
        food_count=len(world.all_food()),
        mutation_counts=mutation_counts,
        agents=agents,
        groups=groups,
    )
