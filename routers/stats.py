import traceback
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import deps
from genome import GENE_RANGES, GENE_DEFAULTS

router = APIRouter()


class AgentStats(BaseModel):
    id: UUID
    x: int
    y: int
    hunger: float
    age: int
    alive: bool
    birth_tick: int


class GeneStat(BaseModel):
    name: str
    avg: float
    default: float
    lo: float
    hi: float
    norm: float  # deviation from default, normalized to [-1, 1]


class WorldStats(BaseModel):
    agent_count: int
    plant_count: int
    gene_stats: list[GeneStat]
    agents: list[AgentStats]


def _gene_stats(living) -> list[GeneStat]:
    stats: list[GeneStat] = []
    for gene, (lo, hi) in GENE_RANGES.items():
        default = GENE_DEFAULTS[gene]
        if living:
            avg = sum(a.behavioral_genome[gene] for a in living) / len(living)
        else:
            avg = default

        if avg >= default:
            denom = hi - default
            norm = (avg - default) / denom if denom > 0 else 0.0
        else:
            denom = default - lo
            norm = (avg - default) / denom if denom > 0 else 0.0

        stats.append(
            GeneStat(
                name=gene,
                avg=avg,
                default=default,
                lo=lo,
                hi=hi,
                norm=max(-1.0, min(1.0, norm)),
            )
        )
    return stats


@router.get("/stats")
async def get_stats():
    try:
        all_agents = deps.agents.all()

        agents = [
            AgentStats(
                id=a.id,
                x=a.x,
                y=a.y,
                hunger=a.needs.hunger,
                age=a.age,
                alive=a.alive,
                birth_tick=a.birth_tick,
            )
            for a in all_agents
        ]

        return WorldStats(
            agent_count=len(agents),
            plant_count=len(deps.vegetation.all_plants),
            gene_stats=_gene_stats(deps.agents.all_living),
            agents=agents,
        )
    except Exception:
        return JSONResponse(status_code=500, content={"error": traceback.format_exc()})
