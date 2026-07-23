"""circuit_breaker boundary test."""
from aios_core.circuit_breaker import CircuitBreaker

def test_initial_state(): from aios_core.circuit_breaker import CircuitState; assert CircuitBreaker().state == CircuitState.CLOSED
