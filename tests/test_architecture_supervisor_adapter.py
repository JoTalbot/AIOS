from __future__ import annotations

from aios_core.architecture import SpecialistInvocation
from aios_core.supervisor import SupervisorTask
from tests.test_architecture_runtime import _runtime


def _task() -> SupervisorTask:
    return SupervisorTask(
        task_id="supervised-1",
        title="Secure capability implementation",
        description="Implement and test security policy",
        risk_level="high",
        budget_agents=4,
    )


def test_selected_specialists_execute_only_through_governed_runtime() -> None:
    runtime, capabilities, budget, policy_audit = _runtime(max_actions=4)
    decision, _ = runtime.plan(_task())
    invocations = {
        candidate.role: SpecialistInvocation(
            agent_id="agent-1",
            capability="execute_tool",
            arguments={"role": candidate.role},
        )
        for candidate in decision.selected
    }

    run = runtime.run_supervised(_task(), invocations)

    selected_roles = {candidate.role for candidate in run.decision.selected}
    assert set(run.observations) == selected_roles
    assert all(result.success for result in run.results)
    assert all(observation.success for observation in run.observations.values())
    assert {call["input_data"]["role"] for call in capabilities.calls} == selected_roles
    assert budget.actions_used == len(selected_roles)
    assert len(policy_audit.get_events()) == len(selected_roles)


def test_policy_denial_stops_supervised_side_effects() -> None:
    runtime, capabilities, budget, _ = _runtime(allowed=False, max_actions=4)
    decision, _ = runtime.plan(_task())
    invocations = {
        candidate.role: SpecialistInvocation("agent-1", "execute_tool")
        for candidate in decision.selected
    }

    run = runtime.run_supervised(_task(), invocations)

    assert run.results[0].success is False
    assert capabilities.calls == []
    assert budget.actions_used == 0
    assert run.observations
    assert all(not observation.success for observation in run.observations.values())


def test_missing_role_invocation_fails_closed() -> None:
    runtime, capabilities, _, _ = _runtime(max_actions=4)

    run = runtime.run_supervised(_task(), {})

    assert run.results[0].success is False
    assert "missing governed invocation" in (run.results[0].error or "")
    assert capabilities.calls == []
