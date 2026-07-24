"""Circuit Breaker Pattern for AIOS v10.5.0.

Enhanced circuit breaker with metrics tracking, state listeners,
half-open probing, fallback functions, configurable thresholds,
and sliding-window failure detection.

Classes:
    CircuitState        — CLOSED / OPEN / HALF_OPEN
    CircuitMetrics      — success/failure/trip/rejection counters
    CircuitBreaker      — enhanced breaker with metrics, listeners, fallback
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ── Metrics ──────────────────────────────────────────────────────────────────

@dataclass
class CircuitMetrics:
    """Tracking counters for circuit breaker events."""
    success_count: int = 0
    failure_count: int = 0
    trip_count: int = 0          # number of times circuit opened
    rejection_count: int = 0     # calls rejected while OPEN
    half_open_successes: int = 0
    half_open_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_call_time: float = 0.0

    def record_success(self, duration: float = 0.0) -> None:
        """Record a successful call."""
        self.success_count += 1
        self.last_success_time = time.time()
        self.total_call_time += duration

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

    def record_trip(self) -> None:
        """Record circuit opening (trip)."""
        self.trip_count += 1

    def record_rejection(self) -> None:
        """Record a rejected call (OPEN state)."""
        self.rejection_count += 1

    def success_rate(self) -> float:
        """Return success rate (0..1)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total


# ── Circuit Breaker ─────────────────────────────────────────────────────────

class CircuitBreaker:
    """Enhanced circuit breaker with metrics, listeners, and fallback.

    Features:
    - Sliding-window failure threshold
    - Half-open probing with configurable probe calls
    - Fallback function for OPEN state
    - State change listeners
    - Detailed metrics tracking
    - Configurable recovery timeout
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        fallback: Callable | None = None,
    ) -> None:
        """Initialize CircuitBreaker.

        Args:
            failure_threshold: Failures before circuit opens.
            recovery_timeout: Seconds before transitioning to HALF_OPEN.
            half_open_max_calls: Allowed calls in HALF_OPEN before deciding state.
            fallback: Function to call when circuit is OPEN (receives *args, **kwargs).
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.fallback = fallback

        self.failure_count: int = 0
        self.last_failure_time: Optional[float] = None
        self.state: CircuitState = CircuitState.CLOSED
        self._half_open_calls: int = 0
        self._listeners: list[Callable[[CircuitState, CircuitState], None]] = []
        self.metrics: CircuitMetrics = CircuitMetrics()

    # ── State transitions ────────────────────────────────────────

    def _transition(self, new_state: CircuitState) -> None:
        """Transition to new state and notify listeners."""
        old = self.state
        self.state = new_state
        logger.info("Circuit breaker transition: %s → %s", old.value, new_state.value)
        for listener in self._listeners:
            try:
                listener(old, new_state)
            except Exception:
                pass

    def _should_try_half_open(self) -> bool:
        """Check if enough time has passed to attempt HALF_OPEN."""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    # ── Public API ───────────────────────────────────────────────

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker.

        If CLOSED → call function, track success/failure.
        If OPEN → check timeout → HALF_OPEN or reject/fallback.
        If HALF_OPEN → limited calls, decide next state.
        """
        # ── OPEN state ──
        if self.state == CircuitState.OPEN:
            if self._should_try_half_open():
                self._transition(CircuitState.HALF_OPEN)
                self._half_open_calls = 0
            else:
                self.metrics.record_rejection()
                if self.fallback:
                    return self.fallback(*args, **kwargs)
                raise CircuitOpenError("Circuit breaker is OPEN")

        # ── HALF_OPEN state ──
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            try:
                start = time.time()
                result = func(*args, **kwargs)
                self.metrics.record_success(time.time() - start)
                self.metrics.half_open_successes += 1
                # If enough successful probes → close circuit
                if self._half_open_calls >= self.half_open_max_calls:
                    self.failure_count = 0
                    self._transition(CircuitState.CLOSED)
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                self.metrics.record_failure()
                self.metrics.half_open_failures += 1
                self._transition(CircuitState.OPEN)
                self.metrics.record_trip()
                if self.fallback:
                    return self.fallback(*args, **kwargs)
                raise

        # ── CLOSED state ──
        try:
            start = time.time()
            result = func(*args, **kwargs)
            self.metrics.record_success(time.time() - start)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.metrics.record_failure()
            if self.failure_count >= self.failure_threshold:
                self._transition(CircuitState.OPEN)
                self.metrics.record_trip()
            raise

    def add_listener(self, listener: Callable[[CircuitState, CircuitState], None]) -> None:
        """Add a state change listener."""
        self._listeners.append(listener)

    def force_open(self) -> None:
        """Manually force circuit to OPEN state."""
        self._transition(CircuitState.OPEN)
        self.metrics.record_trip()

    def force_close(self) -> None:
        """Manually force circuit to CLOSED state."""
        self.failure_count = 0
        self._half_open_calls = 0
        self._transition(CircuitState.CLOSED)

    def reset(self) -> None:
        """Full reset — clear all counters and return to CLOSED."""
        self.failure_count = 0
        self._half_open_calls = 0
        self.last_failure_time = None
        self.metrics = CircuitMetrics()
        self.state = CircuitState.CLOSED

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "metrics": {
                "success_count": self.metrics.success_count,
                "failure_count": self.metrics.failure_count,
                "trip_count": self.metrics.trip_count,
                "rejection_count": self.metrics.rejection_count,
                "success_rate": self.metrics.success_rate(),
            },
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN and no fallback is provided."""
    pass
