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
from plant import VegetationManager
from routers import (
    agents,
    clock as clock_router,
    game,
    logs,
    stats,
    world as world_router,
)
from simulation import Simulation
from world import World

STATIC = Path(__file__).parent.parent / "static"

_world = World(width=100, height=100)
_vegetation = VegetationManager(_world)
_agents = Agents(_world.width, _world.height)
_simulation = Simulation(_world, _vegetation, _agents)

deps.world = _world
deps.vegetation = _vegetation
deps.agents = _agents
deps.simulation = _simulation


async def _on_tick(tick_count: int) -> None:
    import time

    t0 = time.perf_counter()
    try:
        events = deps.simulation.on_tick(tick_count)
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    t1 = time.perf_counter()

    for event_name, data in events:
        await broadcast(event_name, data)

    await broadcast(
        "tick",
        {
            "tick": tick_count,
            "is_night": clock.is_night,
            "day_number": clock.day_number,
            "day_phase": clock.day_phase,
            "diurnal_offset": round(deps.world.weather.diurnal_offset(), 4),
            "clouds": deps.world.weather.clouds_to_list(),
        },
    )
    t2 = time.perf_counter()
    sim_ms = (t1 - t0) * 1000
    broadcast_ms = (t2 - t1) * 1000
    print(
        f"[tick {tick_count:4d}] sim={sim_ms:.1f}ms  broadcast={broadcast_ms:.1f}ms  total={sim_ms+broadcast_ms:.1f}ms"
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
