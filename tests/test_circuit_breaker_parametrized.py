"""Parametrized circuit breaker tests."""

import pytest
from aios_core.circuit_breaker import CircuitBreaker, CircuitState


@pytest.mark.parametrize("threshold,expected_state", [
    (1, CircuitState.OPEN), (2, CircuitState.CLOSED), (3, CircuitState.CLOSED),
])
def test_failure_threshold(threshold, expected_state):
    cb = CircuitBreaker(failure_threshold=threshold)
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
    except ValueError: pass
    assert cb.state == expected_state
