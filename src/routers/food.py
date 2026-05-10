from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from connections import broadcast
from food import Food
from world import world

router = APIRouter(prefix="/food")


class PlaceFoodRequest(BaseModel):
    x: int
    y: int
    value: int = 1


@router.post("", response_model=Food, status_code=201)
async def place_food(body: PlaceFoodRequest) -> Food:
    try:
        food = world.place_food(body.x, body.y, body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await broadcast("food_placed", {"food": food.model_dump(mode="json")})
    return food


@router.get("", response_model=list[Food])
async def list_food() -> list[Food]:
    return world.all_food()


@router.delete("/{food_id}", status_code=204)
async def remove_food(food_id: UUID) -> None:
    food = world.remove_food(food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    await broadcast("food_removed", {"food": food.model_dump(mode="json")})
