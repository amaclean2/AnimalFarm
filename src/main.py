from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import deps
from agents import Agents
from clock import clock
from connections import _connections, broadcast
from food import FoodManager
from routers import (
    agents,
    clock as clock_router,
    food,
    game,
    logs,
    stats,
    world as world_router,
)
from simulation import Simulation
from world import World

STATIC = Path(__file__).parent.parent / "static"

_world = World(width=100, height=100)
_food = FoodManager(_world)
_agents = Agents(_world.width, _world.height)
_simulation = Simulation(_world, _food, _agents)

deps.world = _world
deps.food = _food
deps.agents = _agents
deps.simulation = _simulation


async def _on_tick(tick_count: int) -> None:
    try:
        events = deps.simulation.on_tick(tick_count)
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    for event_name, data in events:
        await broadcast(event_name, data)

    await broadcast(
        "tick",
        {
            "tick": tick_count,
            "is_night": clock.is_night,
            "day_number": clock.day_number,
            "day_phase": clock.day_phase,
            "clouds": deps.world.weather.clouds_to_list(),
        },
    )
    if not deps.agents.all_living:
        clock.stop()
        await broadcast("game_over", {"tick": tick_count})


@asynccontextmanager
async def lifespan(_: FastAPI):
    clock.register(_on_tick)
    yield
    clock.stop()


app = FastAPI(title="Animal Farm API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(food.router)
app.include_router(world_router.router)
app.include_router(clock_router.router)
app.include_router(game.router)
app.include_router(stats.router)
app.include_router(logs.router)

app.mount("/scripts", StaticFiles(directory=STATIC / "scripts"), name="scripts")
app.mount("/styles", StaticFiles(directory=STATIC / "styles"), name="styles")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/world-viewer")
async def world_viewer_page() -> FileResponse:
    return FileResponse(STATIC / "world-viewer.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.remove(websocket)
