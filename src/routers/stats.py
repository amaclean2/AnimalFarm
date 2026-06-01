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
    alive: bool
    birth_tick: int


class WorldStats(BaseModel):
    agent_count: int
    plant_count: int
    mutation_counts: dict[str, int]
    agents: list[AgentStats]


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
                alive=a.alive,
                birth_tick=a.birth_tick,
            )
            for a in all_agents
        ]

        mutation_counts: dict[str, int] = {}
        for a in all_agents:
            for m in a.mutations:
                mutation_counts[m] = mutation_counts.get(m, 0) + 1

        return WorldStats(
            agent_count=len(agents),
            plant_count=len(deps.vegetation.all_plants),
            mutation_counts=mutation_counts,
            agents=agents,
        )
    except Exception:
        return JSONResponse(status_code=500, content={"error": traceback.format_exc()})
