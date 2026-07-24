import contextlib

import pytest

from aios_core.circuit_breaker import CircuitBreaker, CircuitState


@pytest.mark.parametrize("threshold", [1,2,3,5])
def test_opens_after_n_failures(threshold):
    cb = CircuitBreaker(failure_threshold=threshold, recovery_timeout=0.01)
    for _ in range(threshold):
        with contextlib.suppress(ValueError): cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    assert cb.state == CircuitState.OPEN
    import time; time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
