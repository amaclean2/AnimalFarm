import traceback
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import deps

router = APIRouter()


class AgentStats(BaseModel):
    id: UUID
    x: int
    y: int
    hunger: float
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


@router.get("/stats")
async def get_stats():
    try:
        all_agents = deps.agents.all()

        agents = [
            AgentStats(
                id=a.id,
                x=a.x,
                y=a.y,
                hunger=a.hunger,
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
            for g in deps.agents.all_groups
        ]

        return WorldStats(
            agent_count=len(agents),
            group_count=len(groups),
            food_count=len(deps.food.all_food),
            mutation_counts=mutation_counts,
            agents=agents,
            groups=groups,
        )
    except Exception:
        return JSONResponse(status_code=500, content={"error": traceback.format_exc()})
