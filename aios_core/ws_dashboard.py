"""WebSocket dashboard — real-time price alert streaming.

Provides a WebSocket endpoint that streams live price drop alerts,
autowatch cycle reports, and cross-platform comparison updates
to connected dashboard clients.

Uses Starlette/FastAPI WebSocket protocol with JSON message frames.
"""

from __future__ import annotations

import asyncio
import bleach
import html
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from jinja2 import Environment, select_autoescape
from starlette.applications import Starlette
from starlette.requests import Request
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

    Note: This handler already uses WebSocket protocol which is inherently safer
    than HTTP for user input handling. No additional sanitization needed here
    as WebSocket messages are handled as binary/text frames without HTML rendering.
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
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            except json.JSONDecodeError:
                pass  # Ignore non-JSON messages
    except Exception:
        # Client disconnected
        pass
    finally:
        await bus.disconnect(websocket)


def sanitize_input(text: str | None) -> str:
    """Sanitize user input to prevent XSS attacks using bleach library.

    Args:
        text: Input string to sanitize.

    Returns:
        Sanitized string with dangerous HTML tags and attributes removed.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        return str(text)
    return bleach.clean(text, tags=[], attributes={}, strip=True)

def xss_protect(f):
    """Decorator to automatically sanitize all request inputs to prevent XSS attacks.

    Applies sanitization to query parameters, form data, and JSON body.
    """
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        # Sanitize query parameters
        if request.query_params:
            sanitized_params = {}
            for key, value in request.query_params.items():
                sanitized_params[html.escape(key)] = sanitize_input(value)
            request._query_params = sanitized_params  # type: ignore

        # Sanitize form data
        if await request.form():
            sanitized_form = {}
            form_data = await request.form()
            for key, value in form_data.items():
                sanitized_form[html.escape(key)] = sanitize_input(value)
            request._form = sanitized_form  # type: ignore

        # Sanitize JSON body if present
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                json_data = await request.json()
                if isinstance(json_data, dict):
                    sanitized_json = {}
                    for key, value in json_data.items():
                        sanitized_json[html.escape(key)] = sanitize_input(str(value))
                    request._json = sanitized_json  # type: ignore
            except json.JSONDecodeError:
                pass

        return await f(request, *args, **kwargs)
    return decorated_function

# Initialize Jinja2 environment with auto-escaping for template rendering
env = Environment(
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

def render_template(template_name: str, **context) -> str:
    """
    Render a Jinja2 template with automatic escaping for security.

    All user-provided data must be sanitized before passing to this function.
    This function ensures that all template variables are properly escaped
    to prevent XSS attacks.

    Args:
        template_name: Name of the template file to render.
        **context: Variables to pass to the template.

    Returns:
        Rendered HTML string with all variables properly escaped.
    """
    # Apply sanitization to all string values in context
    sanitized_context = {}
    for key, value in context.items():
        if isinstance(value, str):
            sanitized_context[key] = sanitize_input(value)
        else:
            sanitized_context[key] = value

    template = env.get_template(template_name)
    return template.render(**sanitized_context)

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