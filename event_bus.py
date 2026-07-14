from asyncio import Queue

from events import Event

_queue: Queue[Event] = Queue()


def publish(event: Event) -> None:
    _queue.put_nowait(event)


def drain() -> list[Event]:
    events: list[Event] = []
    while not _queue.empty():
        events.append(_queue.get_nowait())
    return events
