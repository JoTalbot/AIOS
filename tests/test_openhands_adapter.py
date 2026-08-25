from dataclasses import dataclass

from aios_core.runtime.contracts import AgentStatus, AgentTask
from aios_core.runtime.openhands_adapter import OpenHandsAdapter


@dataclass
class RawResult:
    status: str = "completed"
    output: str = "done"
    evidence: tuple[str, ...] = ("test evidence",)
    artifacts: tuple[str, ...] = ()
    tests: tuple[str, ...] = ("pytest",)
    risks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    cost: float = 0.1
    duration_ms: int = 120
    verdict: str = "APPROVED"


class Runner:
    def run(self, *, task):
        return RawResult()


class BrokenRunner:
    def run(self, *, task):
        raise RuntimeError("OpenHands unavailable")


def test_adapter_maps_successful_result():
    result = OpenHandsAdapter(Runner())(AgentTask(id="oh-1", goal="build"))
    assert result.status is AgentStatus.COMPLETED
    assert result.output == "done"
    assert result.verdict == "APPROVED"
    assert result.duration_ms == 120


def test_adapter_fails_closed_on_runner_error():
    result = OpenHandsAdapter(BrokenRunner())(AgentTask(id="oh-2", goal="build"))
    assert result.status is AgentStatus.FAILED
    assert "OpenHands unavailable" in result.errors[0]
