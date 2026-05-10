import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

TickCallback = Callable[[int], Awaitable[None]]

TICK_INTERVAL = 0.5


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
