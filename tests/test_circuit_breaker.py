"""Tests for Circuit Breaker"""

from aios_core.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_closes_on_success():
    cb = CircuitBreaker(failure_threshold=3)
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_opens_on_failures():
    cb = CircuitBreaker(failure_threshold=2)

    def failing():
        raise ValueError("fail")

    for _ in range(2):
        try:
            cb.call(failing)
        except:
            pass

    assert cb.state == CircuitState.OPEN