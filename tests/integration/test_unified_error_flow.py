"""Smoke tests for unified error flow."""

from core.runtime.unified_error_flow import UnifiedErrorFlow


def test_error_flow_creation():
    event = UnifiedErrorFlow().handle("runtime", "test")
    assert event.stage == "runtime"
