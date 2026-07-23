"""Parametrized: CB full matrix."""
import pytest
from aios_core.circuit_breaker import CircuitBreaker, CircuitState
import time

@pytest.mark.parametrize("fails,threshold,opens", [
    (1,1,True),(1,2,False),(2,2,True),(2,3,False),(5,5,True),
])
def test_open_condition(fails, threshold, opens):
    cb = CircuitBreaker(failure_threshold=threshold, recovery_timeout=0.01)
    for _ in range(fails):
        try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        except ValueError: pass
    expected = CircuitState.OPEN if opens else CircuitState.CLOSED
    assert cb.state == expected
    if opens:
        time.sleep(0.02)
        assert cb.call(lambda: "ok") == "ok"
