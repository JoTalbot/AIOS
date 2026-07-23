"""Parametrized deep: circuit_breaker."""
import pytest
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.circuit_breaker import CircuitState
@pytest.mark.parametrize("th",[1,2,3,5])
def test_cb(th):
    import time
    cb = CircuitBreaker(th,0.01)
    for _ in range(th):
        try:cb.call(lambda:(_ for _ in()).throw(ValueError()))
        except ValueError:pass
    assert cb.state == CircuitState.OPEN
    time.sleep(0.02)
    assert cb.call(lambda:"ok")=="ok"
    assert cb.state == CircuitState.CLOSED

