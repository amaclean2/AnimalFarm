import json
import random
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import config as cfg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import deps
from world.preview import build_preview

router = APIRouter()

WORLDS_DIR = Path(__file__).parent.parent.parent / "worlds"


@router.get("/world/preview")
async def preview_world_get() -> dict:
    seed = random.randint(0, 999999)
    return build_preview(
        seed=seed, num_springs=cfg.NUM_SPRINGS, elevation_coarse_scale=90.0
    )


class PreviewConfig(BaseModel):
    seed: int | None = None
    num_springs: int = cfg.NUM_SPRINGS
    elevation_coarse_scale: float = 90.0


@router.post("/world/preview")
async def preview_world_post(body: PreviewConfig) -> dict:
    seed = body.seed if body.seed is not None else random.randint(0, 999999)
    return build_preview(
        seed=seed,
        num_springs=body.num_springs,
        elevation_coarse_scale=body.elevation_coarse_scale,
    )


class SaveWorldBody(BaseModel):
    name: str
    seed: int
    config: dict


@router.post("/world/save", status_code=201)
async def save_world(body: SaveWorldBody) -> dict:
    WORLDS_DIR.mkdir(exist_ok=True)
    world_id = str(uuid4())
    data = {
        "id": world_id,
        "name": body.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": body.seed,
        "config": body.config,
    }
    (WORLDS_DIR / f"{world_id}.json").write_text(json.dumps(data, indent=2))
    return data


@router.get("/world/saved")
async def list_saved_worlds() -> list:
    if not WORLDS_DIR.exists():
        return []
    worlds_list = []
    for path in sorted(WORLDS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            worlds_list.append(
                {
                    "id": data["id"],
                    "name": data["name"],
                    "created_at": data["created_at"],
                    "config": data.get("config", {}),
                }
            )
        except Exception:
            pass
    return worlds_list


@router.delete("/world/saved/{world_id}", status_code=204)
async def delete_saved_world(world_id: str) -> None:
    path = WORLDS_DIR / f"{world_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="World not found")
    path.unlink()


@router.get("/world")
async def get_world() -> dict:
    return {
        "width": deps.world.width,
        "height": deps.world.height,
        "agents": [a.model_dump(mode="json") for a in deps.agents.all()],
        "plants": [p.model_dump(mode="json") for p in deps.vegetation.all_plants],
        "rivers": [
            {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
            for r in deps.world.rivers.all_rivers
        ],
        "elevation": deps.world.all_elevation(),
        "temperature": deps.world.weather.base_temperature(),
        "precipitation": deps.world.weather.base_precipitation(),
        "clouds": deps.world.weather.clouds_to_list(),
    }
