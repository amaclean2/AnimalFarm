from fastapi import APIRouter, HTTPException

from clock import clock
from simulation import simulation

router = APIRouter(prefix="/clock")


@router.post("/start", status_code=204)
async def start_clock() -> None:
    if clock.state != "stopped":
        raise HTTPException(status_code=400, detail=f"Clock is already {clock.state}")
    clock.start()


@router.post("/stop", status_code=204)
async def stop_clock() -> None:
    if clock.state == "stopped":
        raise HTTPException(status_code=400, detail="Clock is already stopped")
    clock.stop()
    simulation.save_log()
    simulation.reset()


@router.post("/pause", status_code=204)
async def pause_clock() -> None:
    if clock.state != "running":
        raise HTTPException(status_code=400, detail=f"Clock is {clock.state}, not running")
    clock.pause()


@router.post("/resume", status_code=204)
async def resume_clock() -> None:
    if clock.state != "paused":
        raise HTTPException(status_code=400, detail=f"Clock is {clock.state}, not paused")
    clock.resume()


@router.get("")
async def get_clock() -> dict:
    return {"state": clock.state, "tick_count": clock.tick_count, "interval": clock.interval}
