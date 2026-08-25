from __future__ import annotations

from aios_core.architecture import ArchitectureRuntime
from aios_core.execution import Action, ExecutionContext, ExecutionKernel
from aios_core.kernel import AgentIdentity, AuditLogger, IdentityRegistry, Kernel, PolicyEngine, TrustManager
from aios_core.runtime import AgentBudget, HeartbeatManager, LifecycleManager
from aios_core.supervisor import SupervisorTask


class FakeCapabilities:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return {"success": True, "result": {"executed": kwargs["capability_name"]}}


def _runtime(*, allowed: bool = True, max_actions: int = 1):
    identity = AgentIdentity("agent-1", "developer", ("execute_tool",))
    identities = IdentityRegistry((identity,))
    trust = TrustManager()
    trust.grant(identity.agent_id, "T1")
    policies = PolicyEngine()
    if allowed:
        policies.allow("execute_tool", "T1")
    audit = AuditLogger()
    policy = Kernel(identities, trust, policies, audit)

    lifecycle = LifecycleManager()
    lifecycle.register(identity.agent_id)
    lifecycle.ready(identity.agent_id)
    lifecycle.start(identity.agent_id)
    heartbeat = HeartbeatManager()
    heartbeat.ping(identity.agent_id)
    budget = AgentBudget(max_actions=max_actions)
    capabilities = FakeCapabilities()
    runtime = ArchitectureRuntime(
        policy=policy,
        execution=ExecutionKernel(capabilities),
        lifecycle=lifecycle,
        heartbeat=heartbeat,
        budgets={identity.agent_id: budget},
    )
    return runtime, capabilities, budget, audit


def _request():
    return Action("execute_tool", {"value": "ok"}), ExecutionContext("task-1", "agent-1")


def test_authorized_request_reaches_execution_boundary() -> None:
    runtime, capabilities, budget, audit = _runtime()
    action, context = _request()

    observation = runtime.execute(action, context)

    assert observation.success is True
    assert observation.result == {"executed": "execute_tool"}
    assert len(capabilities.calls) == 1
    assert budget.actions_used == 1
    assert audit.get_events()[0]["allowed"] is True


def test_policy_denial_cannot_reach_side_effect_or_consume_budget() -> None:
    runtime, capabilities, budget, audit = _runtime(allowed=False)
    action, context = _request()

    observation = runtime.execute(action, context)

    assert observation.success is False
    assert observation.error == "policy_denied:missing_policy_grant"
    assert capabilities.calls == []
    assert budget.actions_used == 0
    assert audit.get_events()[0]["allowed"] is False


def test_runtime_health_and_budget_are_enforced_after_policy() -> None:
    runtime, capabilities, budget, _ = _runtime(max_actions=0)
    action, context = _request()

    exhausted = runtime.execute(action, context)
    runtime.lifecycle.stop("agent-1")
    stopped = runtime.execute(action, context)

    assert exhausted.error == "agent action budget exhausted"
    assert stopped.error == "agent_not_running:stopped"
    assert capabilities.calls == []
    assert budget.actions_used == 0


def test_unknown_identity_fails_closed() -> None:
    runtime, capabilities, _, _ = _runtime()
    action = Action("execute_tool")

    observation = runtime.execute(action, ExecutionContext("task-1", "intruder"))

    assert observation.success is False
    assert observation.error.startswith("policy_error:unknown agent identity")
    assert capabilities.calls == []


def test_supervisor_plan_builds_bounded_security_graph() -> None:
    runtime, _, _, _ = _runtime()

    decision, graph = runtime.plan(
        SupervisorTask(
            task_id="task-2",
            title="Secure execution architecture",
            description="Implement and test auth sandbox policy",
            risk_level="high",
            budget_agents=4,
        )
    )

    roles = {candidate.role for candidate in decision.selected}
    assert "security" in roles
    assert len(roles) <= 4
    assert {node.role for node in graph.nodes} == roles
