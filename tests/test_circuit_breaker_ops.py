"""Circuit breaker operations tests."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState
def test_cb_transitions():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError("f")))
    except ValueError: pass
    assert cb.state == CircuitState.OPEN
    import time; time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED
