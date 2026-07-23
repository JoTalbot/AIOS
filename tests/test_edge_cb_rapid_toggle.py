"""Edge: circuit breaker rapid toggle."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState
def test_rapid_toggle():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.001)
    for cycle in range(5):
        try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        except ValueError: pass
        assert cb.state == CircuitState.OPEN
        import time; time.sleep(0.002)
        assert cb.call(lambda: "ok") == "ok"
