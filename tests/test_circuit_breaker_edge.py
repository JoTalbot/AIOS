"""Circuit breaker edge cases."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState

def test_recovery():
    cb = CircuitBreaker(1, 0.001)
    try:
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    except ValueError:
        pass
    import time
    time.sleep(0.002)
    assert cb.call(lambda: "ok") == "ok"
