"""AIOS WebSocket Support v4.2-alpha

Real-time updates for tasks, events, and stats.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Set

from starlette.websockets import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Execute disconnect."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_event(self, event_type: str, data: Any) -> None:
        await self.broadcast(
            {
                "type": event_type,
                "data": data,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        )


# Global manager instance
ws_manager = WebSocketManager()
