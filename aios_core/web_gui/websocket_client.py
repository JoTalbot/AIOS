"""WebSocket client for live dashboard updates."""

from __future__ import annotations

import json
from typing import Any

import httpx


class DashboardWebSocket:
    """Simple WebSocket client for dashboard live updates."""

    def __init__(self, url: str = "http://127.0.0.1:8580/ws/dashboard"):
        self.url = url
        self._listeners: dict[str, list[Any]] = {}

    def on(self, event: str, callback: Any) -> None:
        """Register event listener."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    async def connect(self) -> None:
        """Connect to WebSocket and listen for events."""
        try:
            async with (
                httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client,
                client.stream("GET", self.url) as response,
            ):
                    async for line in response.aiter_text():
                        if line.startswith("{"):
                            try:
                                data = json.loads(line)
                                event = data.get("event", "message")
                                for callback in self._listeners.get(event, []):
                                    callback(data)
                            except Exception:
                                pass
        except Exception:
            pass


dashboard_ws = DashboardWebSocket()
