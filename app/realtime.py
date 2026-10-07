from __future__ import annotations

import json
from datetime import date, datetime, time
from typing import Any, Dict, Optional

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        # socket -> id do usuario autenticado ({tipo:'auth'}) ou None. So o socket
        # de alertas do App.jsx se autentica; os sockets dos paineis (que so
        # recarregam dados) ficam anonimos.
        self._connections: Dict[WebSocket, Optional[int]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[websocket] = None

    def identificar(self, websocket: WebSocket, usuario_id: int) -> None:
        if websocket in self._connections:
            self._connections[websocket] = usuario_id

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, payload: dict[str, Any], excluir_usuario_id: Optional[int] = None) -> None:
        if not self._connections:
            return

        message = json.dumps(payload, ensure_ascii=False, default=_json_default)
        dead: list[WebSocket] = []
        for ws, usuario_id in list(self._connections.items()):
            # Quem fez a acao nao recebe alerta da propria acao.
            if excluir_usuario_id is not None and usuario_id == excluir_usuario_id:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


realtime_manager = RealtimeManager()


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


async def broadcast_event(event_type: str, autor_id: Optional[int] = None, **data: Any) -> None:
    """autor_id = usuario que realizou a acao; o socket de alertas dele nao recebe o evento."""
    payload: dict[str, Any] = {"type": event_type, **data}
    await realtime_manager.broadcast(payload, excluir_usuario_id=autor_id)
