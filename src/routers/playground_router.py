import asyncio
import importlib
import json
import random
import sys
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agent import MAX_HEALTH
from simulation import Simulation
from world import World

PG_WIDTH = 10
PG_HEIGHT = 10

router = APIRouter(prefix="/playground")

_world = World(width=PG_WIDTH, height=PG_HEIGHT)
_sim = Simulation(_world)
_tick = 0
_init_agent = _world.add_agent(PG_WIDTH // 2, PG_HEIGHT // 2)
_agent_id: UUID = _init_agent.id
_sim._game_logged = True  # suppress log writes for playground
_connections: list[WebSocket] = []
_auto_task: asyncio.Task | None = None
_active_scenario: int | None = None
_stop_condition = None  # Callable | None, cached from scenario.stop_when
_scenario_complete: bool = False  # prevents repeated completion events


async def _broadcast(event: str, data: dict) -> None:
    msg = json.dumps({"event": event, **data})
    dead: list[WebSocket] = []
    for ws in _connections:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


def _snapshot() -> dict:
    return {
        "agents": [a.model_dump(mode="json") for a in _world.all_agents()],
        "food": [f.model_dump(mode="json") for f in _world.all_food()],
        "tick": _tick,
        "active_scenario": _active_scenario,
    }


def _load_scenarios():
    name = "playground_scenarios"
    if name in sys.modules:
        mod = importlib.reload(sys.modules[name])
    else:
        mod = importlib.import_module(name)
    return mod.SCENARIOS


def _cancel_auto() -> None:
    global _auto_task
    if _auto_task and not _auto_task.done():
        _auto_task.cancel()
    _auto_task = None


async def _do_step() -> str | None:
    """Run one tick. Returns 'success', 'agent_died', or None (still running)."""
    global _tick, _scenario_complete
    _tick += 1
    events = _sim.on_tick(_tick)
    for event_name, data in events:
        await _broadcast(event_name, data)
    await _broadcast("tick", {"tick": _tick})

    if _scenario_complete:
        return None

    if not _world.all_living_agents():
        _scenario_complete = True
        return "agent_died"

    if _stop_condition is not None:
        try:
            if _stop_condition(_world, _tick):
                _scenario_complete = True
                return "success"
        except Exception:
            pass

    return None


@router.post("/reset", status_code=204)
async def reset_playground() -> None:
    global _tick, _agent_id, _active_scenario, _stop_condition, _scenario_complete
    _cancel_auto()
    _world.reset()
    _sim.reset()
    _sim._game_logged = True  # suppress log writes for playground
    _tick = 0
    _active_scenario = None
    _stop_condition = None
    _scenario_complete = False
    agent = _world.add_agent(PG_WIDTH // 2, PG_HEIGHT // 2)
    _agent_id = agent.id
    await _broadcast("pg_auto", {"running": False})
    await _broadcast("pg_reset", _snapshot())


@router.post("/step", status_code=204)
async def step_once() -> None:
    result = await _do_step()
    if result:
        await _broadcast("pg_scenario_complete", {"result": result, "tick": _tick})


@router.post("/auto/start", status_code=204)
async def start_auto(interval: float = 0.5) -> None:
    global _auto_task
    _cancel_auto()

    async def _run() -> None:
        global _auto_task
        try:
            while True:
                result = await _do_step()
                if result:
                    await _broadcast("pg_scenario_complete", {"result": result, "tick": _tick})
                    break
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
        finally:
            _auto_task = None
            await _broadcast("pg_auto", {"running": False})

    _auto_task = asyncio.create_task(_run())
    await _broadcast("pg_auto", {"running": True})


@router.post("/auto/stop", status_code=204)
async def stop_auto() -> None:
    _cancel_auto()
    await _broadcast("pg_auto", {"running": False})


@router.post("/food/scatter", status_code=204)
async def scatter_food(count: int = 5) -> None:
    agent = _world.get_agent(_agent_id) if _agent_id else None
    placed = []
    attempts = 0
    while len(placed) < count and attempts < 300:
        x = random.randint(0, PG_WIDTH - 1)
        y = random.randint(0, PG_HEIGHT - 1)
        if agent and (x, y) == (agent.x, agent.y):
            attempts += 1
            continue
        if _world.get_food_at(x, y) is None:
            food = _world.place_food(x, y)
            placed.append(food.model_dump(mode="json"))
        attempts += 1
    for food_data in placed:
        await _broadcast("food_placed", {"food": food_data})


@router.post("/food/clear", status_code=204)
async def clear_food() -> None:
    for food in list(_world.all_food()):
        _world.remove_food(food.id)
    await _broadcast("pg_reset", _snapshot())


class ToggleFoodRequest(BaseModel):
    x: int
    y: int


@router.post("/food/toggle", status_code=204)
async def toggle_food(body: ToggleFoodRequest) -> None:
    if not _world.in_bounds(body.x, body.y):
        return
    existing = _world.get_food_at(body.x, body.y)
    if existing:
        _world.remove_food(existing.id)
        await _broadcast("food_removed", {"food": existing.model_dump(mode="json")})
    else:
        agent = _world.get_agent(_agent_id) if _agent_id else None
        if agent and (agent.x, agent.y) == (body.x, body.y):
            return
        food = _world.place_food(body.x, body.y)
        await _broadcast("food_placed", {"food": food.model_dump(mode="json")})


@router.post("/agent/heal", status_code=204)
async def heal_agent() -> None:
    agent = _world.get_agent(_agent_id)
    if agent and agent.alive:
        agent.health = MAX_HEALTH
        await _broadcast("agent_moved", {"agent": agent.model_dump(mode="json")})


@router.post("/agent/damage", status_code=204)
async def damage_agent(amount: int = 20) -> None:
    agent = _world.get_agent(_agent_id)
    if agent and agent.alive:
        agent.health = max(1, agent.health - amount)
        await _broadcast("agent_moved", {"agent": agent.model_dump(mode="json")})


@router.get("/scenarios")
async def list_scenarios() -> dict:
    try:
        scenarios = _load_scenarios()
        return {
            "scenarios": [
                {"index": i, "name": s.name, "description": s.description}
                for i, s in enumerate(scenarios)
            ],
            "error": None,
        }
    except Exception as exc:
        return {"scenarios": [], "error": str(exc)}


@router.post("/scenarios/run", status_code=204)
async def run_scenario(index: int) -> None:
    global _tick, _agent_id, _active_scenario, _stop_condition, _scenario_complete
    try:
        scenarios = _load_scenarios()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if index < 0 or index >= len(scenarios):
        raise HTTPException(status_code=400, detail="Scenario index out of range")
    scenario = scenarios[index]

    _cancel_auto()
    _world.reset()
    _sim.reset()
    _sim._game_logged = True
    _tick = 0
    _active_scenario = index
    _stop_condition = getattr(scenario, "stop_when", None)
    _scenario_complete = False

    agent = _world.add_agent(scenario.agent_x, scenario.agent_y)
    agent.health = scenario.agent_health
    agent.age = scenario.agent_age
    agent.is_adult = scenario.agent_is_adult
    _agent_id = agent.id

    for fx, fy in scenario.food:
        if _world.in_bounds(fx, fy) and (fx, fy) != (scenario.agent_x, scenario.agent_y):
            if _world.get_food_at(fx, fy) is None:
                _world.place_food(fx, fy)

    await _broadcast("pg_auto", {"running": False})
    await _broadcast("pg_reset", _snapshot())


@router.get("/world")
async def get_world() -> dict:
    return _snapshot()


@router.websocket("/ws")
async def playground_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.append(websocket)
    snapshot = _snapshot()
    await websocket.send_text(json.dumps({"event": "pg_reset", **snapshot}))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
