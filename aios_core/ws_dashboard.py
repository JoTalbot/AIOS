"""WebSocket dashboard — real-time price alert streaming.

Provides a WebSocket endpoint that streams live price drop alerts,
autowatch cycle reports, and cross-platform comparison updates
to connected dashboard clients.

Uses Starlette/FastAPI WebSocket protocol with JSON message frames.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute


class WSMessageType(Enum):
    """Types of WebSocket messages streamed to dashboard."""

    PRICE_DROP = "price_drop"
    AUTOWATCH_CYCLE = "autowatch_cycle"
    CROSS_PLATFORM = "cross_platform"
    SYSTEM_STATUS = "system_status"
    FAVORITE_ALERT = "favorite_alert"
    VECTOR_MATCH = "vector_match"


@dataclass
class WSMessage:
    """A single WebSocket message for dashboard streaming."""

    type: WSMessageType
    payload: dict[str, object]
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            {
                "type": self.type.value,
                "payload": self.payload,
                "timestamp": self.timestamp,
                "source": self.source,
            },
            ensure_ascii=False,
        )


class DashboardEventBus:
    """In-memory event bus for streaming dashboard events via WebSocket.

    Maintains a list of connected WebSocket clients and broadcasts
    messages to all of them. Also keeps a buffer of recent events
    for clients that connect late (replay on connect).
    """

    def __init__(self, replay_buffer_size: int = 50) -> None:
        """Initialize DashboardEventBus.

        Args:
            replay_buffer_size: Number of recent events to replay to new clients.
        """
        self._clients: list = []
        self._buffer: list[WSMessage] = []
        self._buffer_size = replay_buffer_size
        self._lock = asyncio.Lock()

    async def connect(self, websocket) -> None:
        """Register a WebSocket client.

        Args:
            websocket: Starlette WebSocket connection.
        """
        async with self._lock:
            self._clients.append(websocket)
            # Replay recent events
            for msg in self._buffer:
                try:  # noqa: SIM105
                    await websocket.send_text(msg.to_json())
                except Exception:
                    pass  # Client disconnected during replay

    async def disconnect(self, websocket) -> None:
        """Remove a WebSocket client.

        Args:
            websocket: Starlette WebSocket connection.
        """
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

    async def broadcast(self, message: WSMessage) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message: WSMessage to send.

        Returns:
            Number of clients that received the message.
        """
        # Add to buffer
        self._buffer.append(message)
        if len(self._buffer) > self._buffer_size:
            self._buffer = self._buffer[-self._buffer_size :]

        sent = 0
        async with self._lock:
            disconnected = []
            for ws in self._clients:
                try:
                    await ws.send_text(message.to_json())
                    sent += 1
                except Exception:
                    disconnected.append(ws)
            # Clean up disconnected clients
            for ws in disconnected:
                self._clients.remove(ws)

        return sent

    def emit_price_drop(self, alert: dict[str, object]) -> WSMessage:
        """Create a price drop alert message (non-async, for call from sync code).

        Args:
            alert: Price drop alert dict from PriceDropAlert.to_dict().

        Returns:
            WSMessage ready for broadcast.
        """
        return WSMessage(
            type=WSMessageType.PRICE_DROP,
            payload=alert,
            source=alert.get("fingerprint", ""),
        )

    def emit_autowatch(self, report: dict[str, object]) -> WSMessage:
        """Create an autowatch cycle report message."""
        return WSMessage(
            type=WSMessageType.AUTOWATCH_CYCLE,
            payload=report,
            source=report.get("platform", ""),
        )

    def emit_cross_platform(self, comparison: dict[str, object]) -> WSMessage:
        """Create a cross-platform comparison message."""
        return WSMessage(
            type=WSMessageType.CROSS_PLATFORM,
            payload=comparison,
            source=comparison.get("group_id", ""),
        )

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)


async def ws_dashboard_handler(websocket) -> None:
    """WebSocket handler for dashboard event streaming.

    On connect: replay recent events.
    While connected: receive JSON commands (subscribe/unsubscribe).
    """
    await websocket.accept()

    bus = websocket.app.state.event_bus
    await bus.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Client can send commands — currently just keep-alive
            try:
                msg = json.loads(data)
                if msg.get("command") == "ping":
                    await websocket.send_text(
                        json.dumps({"type": "pong", "timestamp": time.time()})
                    )
            except json.JSONDecodeError:
                pass  # Ignore non-JSON messages
    except Exception:
        # Client disconnected
        pass
    finally:
        await bus.disconnect(websocket)


def create_ws_dashboard_app(event_bus: DashboardEventBus | None = None) -> Starlette:
    """Create a Starlette app with WebSocket dashboard endpoint.

    Args:
        event_bus: Optional pre-configured event bus.

    Returns:
        Starlette application with /ws/dashboard route.
    """
    bus = event_bus or DashboardEventBus()

    app = Starlette(
        routes=[
            WebSocketRoute("/ws/dashboard", ws_dashboard_handler),
        ],
    )
    app.state.event_bus = bus

    return app
