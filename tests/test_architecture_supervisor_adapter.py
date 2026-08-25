from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aios_core.architecture import DelegationRegistry, SpecialistInvocation
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


def _invocations(decision):
    registry = DelegationRegistry()
    invocations = {}
    for candidate in decision.selected:
        grant = registry.issue(
            owner_id="owner-1",
            delegated_by="supervisor-1",
            task_id="supervised-1",
            role=candidate.role,
            agent_id="agent-1",
            capabilities=frozenset({"execute_tool"}),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        invocations[candidate.role] = SpecialistInvocation(
            agent_id="agent-1",
            capability="execute_tool",
            delegation_id=grant.grant_id,
            arguments={"role": candidate.role},
        )
    return registry, invocations


def test_selected_specialists_execute_only_through_governed_runtime() -> None:
    runtime, capabilities, budget, policy_audit = _runtime(max_actions=4)
    decision, _ = runtime.plan(_task())
    delegations, invocations = _invocations(decision)

    run = runtime.run_supervised(_task(), invocations, delegations)

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
    delegations, invocations = _invocations(decision)

    run = runtime.run_supervised(_task(), invocations, delegations)

    assert run.results[0].success is False
    assert capabilities.calls == []
    assert budget.actions_used == 0
    assert run.observations
    assert all(not observation.success for observation in run.observations.values())


def test_missing_role_invocation_fails_closed() -> None:
    runtime, capabilities, _, _ = _runtime(max_actions=4)

    run = runtime.run_supervised(_task(), {}, DelegationRegistry())

    assert run.results[0].success is False
    assert "missing governed invocation" in (run.results[0].error or "")
    assert capabilities.calls == []


def test_expired_delegation_blocks_specialist() -> None:
    runtime, capabilities, _, _ = _runtime(max_actions=4)
    decision, _ = runtime.plan(_task())
    delegations, invocations = _invocations(decision)
    first = next(iter(invocations.values()))
    delegations.grants[first.delegation_id].expires_at = datetime.now(UTC) - timedelta(seconds=1)

    run = runtime.run_supervised(_task(), invocations, delegations)

    assert any("delegation grant expired" in (result.error or "") for result in run.results)
    assert len(capabilities.calls) < len(decision.selected)


def test_delegation_cannot_expand_capability_or_task_scope() -> None:
    registry = DelegationRegistry()
    grant = registry.issue(
        owner_id="owner-1",
        delegated_by="supervisor-1",
        task_id="task-a",
        role="coder",
        agent_id="agent-1",
        capabilities=frozenset({"read"}),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    for kwargs in (
        {"task_id": "task-b", "role": "coder", "agent_id": "agent-1", "capability": "read"},
        {"task_id": "task-a", "role": "coder", "agent_id": "agent-1", "capability": "write"},
    ):
        try:
            registry.validate(grant.grant_id, **kwargs)
        except RuntimeError:
            pass
        else:
            raise AssertionError("out-of-scope delegation must fail closed")

    registry.revoke(grant.grant_id)
    try:
        registry.validate(
            grant.grant_id,
            task_id="task-a",
            role="coder",
            agent_id="agent-1",
            capability="read",
        )
    except RuntimeError as exc:
        assert "revoked" in str(exc)
    else:
        raise AssertionError("revoked delegation must fail closed")
