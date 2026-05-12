import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Literal

TickCallback = Callable[[int], Awaitable[None]]

TICK_INTERVAL = float(os.getenv("TICK_INTERVAL", "0.3"))
DAY_LENGTH = int(os.getenv("DAY_LENGTH", "60"))


class GameClock:
    def __init__(self, interval: float = TICK_INTERVAL) -> None:
        self.interval = interval
        self.tick_count: int = 0
        self._state: Literal["stopped", "running", "paused"] = "stopped"
        self._task: asyncio.Task | None = None
        self._callbacks: list[TickCallback] = []

    @property
    def state(self) -> Literal["stopped", "running", "paused"]:
        return self._state

    @property
    def is_night(self) -> bool:
        return (self.tick_count % DAY_LENGTH) >= DAY_LENGTH // 2

    @property
    def day_number(self) -> int:
        return self.tick_count // DAY_LENGTH + 1

    @property
    def day_phase(self) -> float:
        """Fraction through the current day/night cycle, 0.0–1.0."""
        return (self.tick_count % DAY_LENGTH) / DAY_LENGTH

    def register(self, callback: TickCallback) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        if self._state != "stopped":
            return
        self.tick_count = 0
        self._state = "running"
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        self._state = "stopped"
        if self._task:
            self._task.cancel()
            self._task = None

    def pause(self) -> None:
        if self._state == "running":
            self._state = "paused"

    def resume(self) -> None:
        if self._state == "paused":
            self._state = "running"

    async def _run(self) -> None:
        while self._state != "stopped":
            await asyncio.sleep(self.interval)
            if self._state == "running":
                self.tick_count += 1
                for cb in self._callbacks:
                    await cb(self.tick_count)


clock = GameClock()
