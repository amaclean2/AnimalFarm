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
    cause_of_death: str
    age: int
    alive: bool
    birth_tick: int
    fruits_harvested: int


class GeneStat(BaseModel):
    name: str
    avg: float
    default: float
    lo: float
    hi: float
    norm: float  # deviation from default, normalized to [-1, 1]


class ScoringMatrixChange(BaseModel):
    state: str
    action: str
    before: float | None
    after: float
    delta: float | None


class WorldStats(BaseModel):
    tick_count: int
    agent_count: int
    plant_count: int
    gene_stats: list[GeneStat]
    agents: list[AgentStats]
    scoring_matrix_changes: list[ScoringMatrixChange]


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
                cause_of_death=a.cause_of_death or "-",
                age=a.age,
                alive=a.alive,
                birth_tick=a.birth_tick,
                fruits_harvested=a.fruits_harvested,
            )
            for a in all_agents
        ]

        return WorldStats(
            tick_count=deps.simulation.tick_count,
            agent_count=len(agents),
            plant_count=len(deps.vegetation.all_plants),
            gene_stats=_gene_stats(deps.agents.all_living),
            agents=agents,
            scoring_matrix_changes=[
                ScoringMatrixChange(
                    state=state, action=action, before=before, after=after, delta=delta
                )
                for state, action, before, after, delta in deps.scoring_matrix.compare_snapshots()
            ],
        )
    except Exception:
        return JSONResponse(status_code=500, content={"error": traceback.format_exc()})
