from __future__ import annotations

from types import SimpleNamespace

from aios_core.architecture import ApprovalGate, ArchitectureAuditStore, ArchitectureRuntime
from aios_core.architecture.openhands_adapter import (
    OPENHANDS_RUN_CAPABILITY,
    GovernedOpenHandsRunner,
    OpenHandsCapabilityAdapter,
)
from aios_core.execution import ExecutionKernel
from aios_core.kernel import AgentIdentity, AuditLogger, IdentityRegistry, Kernel, PolicyEngine, TrustManager
from aios_core.runtime import AgentBudget, HeartbeatManager, LifecycleManager


class FakeContour:
    def __init__(self, status: str = "completed") -> None:
        self.status = status
        self.task_ids: list[str] = []

    def run_task(self, task_id: str):
        self.task_ids.append(task_id)
        return SimpleNamespace(status=self.status, error=None)


def _governed(tmp_path, *, allow: bool = True):
    identity = AgentIdentity("openhands-agent", "coder", (OPENHANDS_RUN_CAPABILITY,))
    policies = PolicyEngine()
    if allow:
        policies.allow(OPENHANDS_RUN_CAPABILITY, "T2")
    trust = TrustManager()
    trust.grant(identity.agent_id, "T2")
    policy = Kernel(IdentityRegistry((identity,)), trust, policies, AuditLogger())
    contour = FakeContour()
    adapter = OpenHandsCapabilityAdapter(contour)
    lifecycle = LifecycleManager()
    lifecycle.register(identity.agent_id)
    lifecycle.ready(identity.agent_id)
    lifecycle.start(identity.agent_id)
    heartbeat = HeartbeatManager()
    heartbeat.ping(identity.agent_id)
    approval = ApprovalGate(frozenset({OPENHANDS_RUN_CAPABILITY}))
    audit = ArchitectureAuditStore(tmp_path / "architecture.jsonl")
    runtime = ArchitectureRuntime(
        policy=policy,
        execution=ExecutionKernel(adapter),
        lifecycle=lifecycle,
        heartbeat=heartbeat,
        budgets={identity.agent_id: AgentBudget(max_actions=1)},
        approval=approval,
        audit=audit,
    )
    return GovernedOpenHandsRunner(runtime), contour, approval, audit


def test_openhands_cloud_run_requires_approval_before_contour(tmp_path) -> None:
    runner, contour, approval, audit = _governed(tmp_path)

    pending = runner.run("task-1", agent_id="openhands-agent")
    approval.decide("openhands-task-1", approved=True, decided_by="owner")
    completed = runner.run("task-1", agent_id="openhands-agent")

    assert pending.error == "approval_pending:openhands-task-1"
    assert completed.success is True
    assert contour.task_ids == ["task-1"]
    assert audit.verify() is True


def test_policy_denial_never_calls_openhands_contour(tmp_path) -> None:
    runner, contour, _, _ = _governed(tmp_path, allow=False)

    denied = runner.run("task-2", agent_id="openhands-agent")

    assert denied.error == "policy_denied:missing_policy_grant"
    assert contour.task_ids == []
