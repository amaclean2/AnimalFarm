import config as cfg

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import deps
from clock import clock

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
    deps.simulation.save_log()
    cfg.reset_runtime()
    deps.simulation.reset()


@router.post("/pause", status_code=204)
async def pause_clock() -> None:
    if clock.state != "running":
        raise HTTPException(
            status_code=400, detail=f"Clock is {clock.state}, not running"
        )
    clock.pause()


@router.post("/resume", status_code=204)
async def resume_clock() -> None:
    if clock.state != "paused":
        raise HTTPException(
            status_code=400, detail=f"Clock is {clock.state}, not paused"
        )
    clock.resume()


class SpeedBody(BaseModel):
    interval: float


@router.post("/speed", status_code=204)
async def set_speed(body: SpeedBody) -> None:
    clock.set_target_gap(max(0.05, min(2.0, body.interval)))


class ObservedGapBody(BaseModel):
    gap_ms: float


@router.post("/observed-gap", status_code=204)
async def post_observed_gap(body: ObservedGapBody) -> None:
    if clock.state == "running":
        clock.adjust_from_observed_gap(body.gap_ms / 1000.0)


@router.get("")
async def get_clock() -> dict:
    return {
        "state": clock.state,
        "tick_count": clock.tick_count,
        "interval": clock.target_gap,
        "is_night": clock.is_night,
        "day_number": clock.day_number,
        "day_phase": clock.day_phase,
    }
