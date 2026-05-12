import importlib
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))

router = APIRouter(prefix="/tests")


def _load_test_cases():
    name = "test_cases"
    if name in sys.modules:
        mod = importlib.reload(sys.modules[name])
    else:
        mod = importlib.import_module(name)
    return mod.TEST_CASES


def _run_one(tc, index: int) -> dict:
    from world import World
    from simulation import Simulation

    world = World(width=10, height=10)
    sim = Simulation(world)
    sim._game_logged = True

    agent = world.add_agent(tc.agent_x, tc.agent_y)
    agent.health = tc.agent_health
    agent.age = tc.agent_age
    agent.is_adult = tc.agent_is_adult
    for x, y in tc.food:
        if world.get_food_at(x, y) is None:
            world.place_food(x, y)
    stop = tc.stop_when or (lambda w, t: False)
    final_tick = None
    for t in range(1, tc.max_ticks + 1):
        sim.on_tick(t)
        if stop(world, t):
            final_tick = t
            break

    passed = bool(tc.assert_fn(world, agent, final_tick))
    return {
        "index": index,
        "name": tc.name,
        "description": tc.description,
        "passed": passed,
        "ticks": final_tick,
        "max_ticks": tc.max_ticks,
        "failure_message": tc.failure_message if not passed else None,
    }


@router.get("")
async def list_tests() -> dict:
    try:
        tcs = _load_test_cases()
        return {
            "tests": [
                {"index": i, "name": tc.name, "description": tc.description, "max_ticks": tc.max_ticks}
                for i, tc in enumerate(tcs)
            ],
            "error": None,
        }
    except Exception as exc:
        return {"tests": [], "error": str(exc)}


@router.post("/run")
async def run_all() -> dict:
    try:
        tcs = _load_test_cases()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    results = [_run_one(tc, i) for i, tc in enumerate(tcs)]
    passed = sum(1 for r in results if r["passed"])
    return {"results": results, "total": len(results), "passed": passed, "failed": len(results) - passed}


@router.post("/run/{index}")
async def run_one(index: int) -> dict:
    try:
        tcs = _load_test_cases()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if index < 0 or index >= len(tcs):
        raise HTTPException(status_code=400, detail="Index out of range")
    return _run_one(tcs[index], index)
