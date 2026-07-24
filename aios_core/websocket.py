"""AIOS WebSocket Support v4.2

Real-time updates for tasks, events, and stats.
Provides topic-based channels, connection metadata, heartbeat,
reconnection helpers, and rate-limited broadcast.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from starlette.websockets import WebSocket

__all__ = ["WebSocketManager", "ws_manager"]

# Sentinel for missing library in test environments
_STARLETTE_AVAILABLE = True


class ConnectionInfo:
    """Metadata tracked per connected WebSocket client."""

    __slots__ = ("ws", "connected_at", "topics", "last_ping", "client_id")

    def __init__(self, ws: WebSocket, client_id: str = ""):
        self.ws = ws
        self.connected_at = time.time()
        self.topics: set[str] = set()
        self.last_ping: float = time.time()
        self.client_id = client_id or str(id(ws))


class WebSocketManager:
    """Manages WebSocket connections for real-time updates.

    Features:
    - Topic-based channel subscriptions
    - Connection metadata and heartbeat tracking
    - Rate-limited broadcast (max messages per second per connection)
    - Message type routing (task_update, event, stats, notification)
    - Safe disconnect handling with cleanup
    """

    def __init__(
        self,
        max_messages_per_second: int = 50,
        heartbeat_interval: float = 30.0,
    ):
        """Initialize WebSocketManager."""
        self._connections: dict[str, ConnectionInfo] = {}
        self._topic_subscribers: dict[str, set[str]] = defaultdict(set)
        self._rate_limits: dict[str, list[float]] = {}
        self._max_msgs_per_sec = max_messages_per_second
        self._heartbeat_interval = heartbeat_interval
        self._message_count: int = 0
        self._broadcast_count: int = 0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self, websocket: WebSocket, client_id: str = "", topics: list[str] = []
    ) -> str:
        """Accept *websocket* and register it with optional *topics*."""
        await websocket.accept()
        info = ConnectionInfo(websocket, client_id)
        conn_id = info.client_id
        self._connections[conn_id] = info
        self._rate_limits[conn_id] = []

        # Auto-subscribe to provided topics
        for topic in topics:
            self.subscribe(conn_id, topic)

        # Send welcome message
        await self._safe_send(
            conn_id,
            {
                "type": "connected",
                "client_id": conn_id,
                "heartbeat_interval": self._heartbeat_interval,
                "available_topics": list(self._topic_subscribers.keys()),
            },
        )
        return conn_id

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove *websocket* from all tracking structures."""
        conn_id = self._find_conn_id(websocket)
        if conn_id is None:
            # Fallback: remove by object identity from legacy set if exists
            return
        info = self._connections.pop(conn_id, None)
        if info:
            for topic in info.topics:
                self._topic_subscribers[topic].discard(conn_id)
        self._rate_limits.pop(conn_id, None)

    def disconnect_by_id(self, conn_id: str) -> None:
        """Remove connection by its *conn_id*."""
        info = self._connections.pop(conn_id, None)
        if info:
            for topic in info.topics:
                self._topic_subscribers[topic].discard(conn_id)
        self._rate_limits.pop(conn_id, None)

    # ------------------------------------------------------------------
    # Topic subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, conn_id: str, topic: str) -> bool:
        """Subscribe *conn_id* to *topic* for targeted broadcasts."""
        info = self._connections.get(conn_id)
        if info is None:
            return False
        info.topics.add(topic)
        self._topic_subscribers[topic].add(conn_id)
        return True

    def unsubscribe(self, conn_id: str, topic: str) -> bool:
        """Remove *conn_id* from *topic*."""
        info = self._connections.get(conn_id)
        if info is None:
            return False
        info.topics.discard(topic)
        self._topic_subscribers[topic].discard(conn_id)
        return True

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def broadcast(self, message: dict[str, Any], topic: str | None = None) -> int:
        """Send *message* to all clients (or only those subscribed to *topic*).

        Returns the number of clients that received the message.
        """
        if topic:
            targets = [
                cid
                for cid in self._topic_subscribers.get(topic, set())
                if cid in self._connections
            ]
        else:
            targets = list(self._connections.keys())

        sent = 0
        disconnected: list[str] = []

        for conn_id in targets:
            if self._check_rate(conn_id):
                success = await self._safe_send(conn_id, message)
                if success:
                    sent += 1
                else:
                    disconnected.append(conn_id)
            # Rate-limited: silently skip

        for cid in disconnected:
            self.disconnect_by_id(cid)

        self._broadcast_count += 1
        self._message_count += sent
        return sent

    async def send_to(self, conn_id: str, message: dict[str, Any]) -> bool:
        """Send *message* to a specific *conn_id*."""
        if not self._check_rate(conn_id):
            return False
        success = await self._safe_send(conn_id, message)
        if not success:
            self.disconnect_by_id(conn_id)
        self._message_count += 1
        return success

    async def send_event(
        self, event_type: str, data: Any, topic: str | None = None
    ) -> int:
        """Send a typed event to all or topic-filtered clients."""
        msg = {
            "type": event_type,
            "data": data,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        return await self.broadcast(msg, topic)

    # ------------------------------------------------------------------
    # Heartbeat / health
    # ------------------------------------------------------------------

    async def ping_all(self) -> dict[str, bool]:
        """Send ping to all connections; return map of conn_id → alive."""
        results: dict[str, bool] = {}
        dead: list[str] = []
        for conn_id, info in self._connections.items():
            alive = await self._safe_send(conn_id, {"type": "ping"})
            results[conn_id] = alive
            if alive:
                info.last_ping = time.time()
            else:
                dead.append(conn_id)
        for cid in dead:
            self.disconnect_by_id(cid)
        return results

    def get_stale_connections(self, timeout: float = 60.0) -> list[str]:
        """Return conn_ids that haven't responded to ping within *timeout* seconds."""
        now = time.time()
        stale = []
        for conn_id, info in self._connections.items():
            if now - info.last_ping > timeout:
                stale.append(conn_id)
        return stale

    async def cleanup_stale(self, timeout: float = 60.0) -> int:
        """Disconnect all stale connections.  Returns count removed."""
        stale = self.get_stale_connections(timeout)
        for cid in stale:
            self.disconnect_by_id(cid)
        return len(stale)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_conn_id(self, ws: WebSocket) -> str | None:
        """Find the conn_id for a WebSocket object."""
        for cid, info in self._connections.items():
            if info.ws is ws:
                return cid
        return None

    async def _safe_send(self, conn_id: str, message: dict) -> bool:
        """Send *message* to *conn_id*; return False if connection failed."""
        info = self._connections.get(conn_id)
        if info is None:
            return False
        try:
            await info.ws.send_json(message)
            return True
        except Exception:
            return False

    def _check_rate(self, conn_id: str) -> bool:
        """Enforce per-connection rate limit.  Returns True if allowed."""
        now = time.time()
        timestamps = self._rate_limits.get(conn_id, [])
        # Prune timestamps older than 1 second
        recent = [t for t in timestamps if now - t < 1.0]
        self._rate_limits[conn_id] = recent
        if len(recent) >= self._max_msgs_per_sec:
            return False
        recent.append(now)
        self._rate_limits[conn_id] = recent
        return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return manager statistics."""
        return {
            "active_connections": len(self._connections),
            "total_topics": len(self._topic_subscribers),
            "total_messages_sent": self._message_count,
            "total_broadcasts": self._broadcast_count,
            "max_messages_per_second": self._max_msgs_per_sec,
            "heartbeat_interval": self._heartbeat_interval,
            "topics": dict(
                (t, len(subs)) for t, subs in self._topic_subscribers.items()
            ),
        }


# Global manager instance
ws_manager = WebSocketManager()
