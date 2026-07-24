"""Tests for aios_core/circuit_breaker.py"""
from __future__ import annotations
import pytest
from aios_core.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    def test_create(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb is not None

    def test_call_success(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        result = cb.call(lambda: "ok")
        assert result == "ok"

    def test_call_failure(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

    def test_add_listener(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.add_listener(lambda event: None)

    def test_force_open(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.force_open()

    def test_force_close(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.force_open()
        cb.force_close()

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.reset()

    def test_stats(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        s = cb.stats()
        assert isinstance(s, dict)
        assert "state" in s or "total_calls" in s or "success_rate" in s
