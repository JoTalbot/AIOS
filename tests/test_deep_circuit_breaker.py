"""Deep circuit breaker — state machine."""
from aios_core.circuit_breaker import CircuitBreaker, CircuitState
def test_full_state_machine():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
    assert cb.state == CircuitState.CLOSED
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    except ValueError: pass
    assert cb.state == CircuitState.CLOSED
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    except ValueError: pass
    assert cb.state == CircuitState.OPEN
    try: cb.call(lambda: "should_not_run"); assert False
    except Exception: pass
    import time; time.sleep(0.02)
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.state == CircuitState.CLOSED
