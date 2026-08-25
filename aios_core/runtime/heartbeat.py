"""Monotonic heartbeat tracking for runtime agents."""

from __future__ import annotations

import time
from collections.abc import Callable


class HeartbeatManager:
    """Track liveness against a bounded monotonic timeout."""

    def __init__(self, timeout_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self._clock = clock
        self.timestamps: dict[str, float] = {}

    def ping(self, agent_id: str) -> None:
        """Record a heartbeat using a clock unaffected by wall-time changes."""
        self.timestamps[agent_id] = self._clock()

    def alive(self, agent_id: str) -> bool:
        """Return whether the last heartbeat is within the configured timeout."""
        timestamp = self.timestamps.get(agent_id)
        return timestamp is not None and self._clock() - timestamp <= self.timeout_seconds
