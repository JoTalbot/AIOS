"""test_circuit_breaker_scenario test."""
import contextlib

from aios_core.circuit_breaker import CircuitBreaker, CircuitState


def test_full_lifecycle():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01, half_open_max_calls=1)
    assert cb.state == CircuitState.CLOSED
    for _ in range(2):
        with contextlib.suppress(ValueError): cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    assert cb.state == CircuitState.OPEN
    import time; time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED
