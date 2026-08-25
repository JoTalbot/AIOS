from types import SimpleNamespace

from aios_core.runtime.contracts import AgentStatus, AgentTask
from aios_core.runtime.openhands_adapter import OpenHandsRuntimeAdapter


def test_runtime_adapter_maps_completed_orchestrator():
    orchestrator = SimpleNamespace(run=lambda **kwargs: SimpleNamespace(status="completed", report=None, error=None, extras=SimpleNamespace(artifacts=())))
    result = OpenHandsRuntimeAdapter(orchestrator)(AgentTask(id="rt-1", goal="build"))
    assert result.status is AgentStatus.COMPLETED
    assert result.verdict == "APPROVED"


def test_runtime_adapter_maps_failed_orchestrator():
    orchestrator = SimpleNamespace(run=lambda **kwargs: SimpleNamespace(status="failed", report=SimpleNamespace(reason="tests failed", last_error="boom"), error="boom", extras=SimpleNamespace(artifacts=())))
    result = OpenHandsRuntimeAdapter(orchestrator)(AgentTask(id="rt-2", goal="build"))
    assert result.status is AgentStatus.FAILED
    assert "boom" in result.errors
