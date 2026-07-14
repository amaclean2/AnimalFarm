from fastapi import WebSocket

_connections: list[WebSocket] = []


async def broadcast(event: str, data: dict) -> None:
    payload = {"event": event, **data}
    for ws in list(_connections):
        await ws.send_json(payload)
