from fastapi import APIRouter

from world import world

router = APIRouter()


@router.get("/world")
async def get_world() -> dict:
    return {
        "width": world.width,
        "height": world.height,
        "agents": [a.model_dump(mode="json") for a in world.all_agents()],
        "food": [f.model_dump(mode="json") for f in world.all_food()],
        "rivers": [
            {"river_id": str(r.id), "tiles": list(r.tiles), "complete": r.complete}
            for r in world.all_rivers()
        ],
        "groups": [
            {"id": str(g.id)}
            for g in world.all_groups()
        ],
    }
