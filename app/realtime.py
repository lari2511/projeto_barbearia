from __future__ import annotations

import json
from typing import Any, Set

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._connections:
            return

        message = json.dumps(payload, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


realtime_manager = RealtimeManager()


async def broadcast_event(event_type: str, **data: Any) -> None:
    payload: dict[str, Any] = {"type": event_type, **data}
    await realtime_manager.broadcast(payload)
