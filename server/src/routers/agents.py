from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent import Agent
from clock import clock
from connections import broadcast
from world import world

router = APIRouter(prefix="/agents")


class CreateAgentRequest(BaseModel):
    x: int
    y: int


@router.post("", response_model=Agent, status_code=201)
async def create_agent(body: CreateAgentRequest) -> Agent:
    try:
        agent = world.add_agent(body.x, body.y, birth_tick=clock.tick_count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await broadcast("agent_created", {"agent": agent.model_dump(mode="json")})
    return agent


@router.get("", response_model=list[Agent])
async def list_agents() -> list[Agent]:
    return world.all_agents()


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID) -> Agent:
    agent = world.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
