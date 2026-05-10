from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from clock import clock
from connections import _connections, broadcast
from routers import agents, clock as clock_router, food, game, stats, world
from simulation import simulation

STATIC = Path(__file__).parent.parent / "static"


async def _on_tick(tick_count: int) -> None:
    events = simulation.on_tick(tick_count)
    for event_name, data in events:
        await broadcast(event_name, data)
    await broadcast("tick", {"tick": tick_count})


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
app.include_router(world.router)
app.include_router(clock_router.router)
app.include_router(game.router)
app.include_router(stats.router)

app.mount("/scripts", StaticFiles(directory=STATIC / "scripts"), name="scripts")
app.mount("/styles",  StaticFiles(directory=STATIC / "styles"),  name="styles")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


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
