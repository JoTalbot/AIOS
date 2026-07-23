"""Edge: circuit breaker with zero threshold."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState

def test_zero_threshold_always_open():
    cb = CircuitBreaker(failure_threshold=0, recovery_timeout=0.001)
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    except ValueError: pass
    assert cb.state == CircuitState.OPEN
    import time; time.sleep(0.002)
    assert cb.call(lambda: "ok") == "ok"
