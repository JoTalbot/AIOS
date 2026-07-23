"""test_circuit_breaker_scenario test."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState

def test_full_lifecycle():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
    assert cb.state == CircuitState.CLOSED
    for _ in range(2):
        try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        except ValueError: pass
    assert cb.state == CircuitState.OPEN
    import time; time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED
