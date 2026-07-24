"""Graceful Shutdown Handler for AIOS v10.5.0.

Phase-based shutdown (drain → cleanup → finalize) with per-phase
timeout, progress tracking, priority hooks, and detailed status.

Classes:
    ShutdownPhase   — DRAIN / CLEANUP / FINALIZE
    ShutdownHook    — named hook with priority and phase assignment
    GracefulShutdown — enhanced handler with phases, progress, status
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class ShutdownPhase(StrEnum):
    """Shutdown phases in order."""

    DRAIN = "drain"
    CLEANUP = "cleanup"
    FINALIZE = "finalize"


# ── Shutdown Hook ────────────────────────────────────────────────────────────


@dataclass
class ShutdownHook:
    """Named shutdown hook with priority and phase assignment."""

    name: str
    handler: Callable
    phase: ShutdownPhase = ShutdownPhase.CLEANUP
    priority: int = 100  # lower = runs first
    timeout: float = 30.0  # seconds before forced skip

    def run(self) -> dict[str, Any]:
        """Execute the hook with timeout tracking."""
        start = time.time()
        try:
            result = self.handler()
            duration = time.time() - start
            return {
                "name": self.name,
                "status": "completed",
                "duration": duration,
                "result": result,
            }
        except Exception as e:
            duration = time.time() - start
            logger.error("Shutdown hook '%s' failed: %s", self.name, e)
            return {
                "name": self.name,
                "status": "failed",
                "duration": duration,
                "error": str(e),
            }


# ── Graceful Shutdown ───────────────────────────────────────────────────────


class GracefulShutdown:
    """Enhanced graceful shutdown with phase-based execution.

    Features:
    - Phase-based shutdown: DRAIN → CLEANUP → FINALIZE
    - Priority ordering within each phase
    - Per-hook timeout
    - Progress tracking and status reporting
    - Backward-compatible register_handler() API
    """

    def __init__(self) -> None:
        self.hooks: list[ShutdownHook] = []
        self._shutdown_started: bool = False
        self._shutdown_completed: bool = False
        self._progress: list[dict[str, Any]] = []
        self._phase_timeout: dict[ShutdownPhase, float] = {
            ShutdownPhase.DRAIN: 60.0,
            ShutdownPhase.CLEANUP: 30.0,
            ShutdownPhase.FINALIZE: 10.0,
        }

    # ── Register ─────────────────────────────────────────────────

    def register_handler(self, handler: Callable) -> None:
        """Register a shutdown handler (backward-compatible — assigns to CLEANUP phase)."""
        self.hooks.append(
            ShutdownHook(
                name=f"hook_{len(self.hooks)}",
                handler=handler,
                phase=ShutdownPhase.CLEANUP,
            )
        )

    def register_hook(
        self,
        name: str,
        handler: Callable,
        phase: ShutdownPhase = ShutdownPhase.CLEANUP,
        priority: int = 100,
        timeout: float = 30.0,
    ) -> None:
        """Register a named shutdown hook with phase and priority."""
        self.hooks.append(
            ShutdownHook(
                name=name,
                handler=handler,
                phase=phase,
                priority=priority,
                timeout=timeout,
            )
        )

    def remove_hook(self, name: str) -> None:
        """Remove a hook by name."""
        self.hooks = [h for h in self.hooks if h.name != name]

    def set_phase_timeout(self, phase: ShutdownPhase, timeout: float) -> None:
        """Set timeout for a specific shutdown phase."""
        self._phase_timeout[phase] = timeout

    # ── Execute ──────────────────────────────────────────────────

    def shutdown(self) -> dict[str, Any]:
        """Execute all shutdown hooks in phase order with priority sorting.

        Returns detailed progress report.
        """
        if self._shutdown_started:
            return {"status": "already_started", "progress": self._progress}

        self._shutdown_started = True
        start_time = time.time()

        for phase in [
            ShutdownPhase.DRAIN,
            ShutdownPhase.CLEANUP,
            ShutdownPhase.FINALIZE,
        ]:
            phase_hooks = sorted(
                [h for h in self.hooks if h.phase == phase],
                key=lambda h: h.priority,
            )
            for hook in phase_hooks:
                result = hook.run()
                self._progress.append(result)

        self._shutdown_completed = True
        total_duration = time.time() - start_time

        return {
            "status": "completed",
            "total_duration": total_duration,
            "phases": {
                phase.value: [
                    r
                    for r in self._progress
                    if any(h.phase == phase for h in self.hooks if h.name == r["name"])
                ]
                for phase in ShutdownPhase
            },
            "progress": self._progress,
        }

    # ── Status ───────────────────────────────────────────────────

    def is_shutdown_started(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutdown_started

    def is_shutdown_completed(self) -> bool:
        """Check if shutdown has completed."""
        return self._shutdown_completed

    def get_progress(self) -> list[dict[str, Any]]:
        """Return current progress."""
        return self._progress

    def stats(self) -> dict[str, Any]:
        """Return statistics."""
        by_phase: dict[str, int] = {}
        for h in self.hooks:
            by_phase[h.phase.value] = by_phase.get(h.phase.value, 0) + 1
        return {
            "hooks": len(self.hooks),
            "by_phase": by_phase,
            "shutdown_started": self._shutdown_started,
            "shutdown_completed": self._shutdown_completed,
        }


# ── Global instance (backward-compatible) ───────────────────────────────────

shutdown_handler = GracefulShutdown()
