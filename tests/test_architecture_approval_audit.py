from __future__ import annotations

import json

from aios_core.architecture import ApprovalGate, ApprovalStatus, ArchitectureAuditStore
from aios_core.execution import Action, ExecutionContext
from tests.test_architecture_runtime import _request, _runtime


def test_high_risk_action_waits_for_one_shot_approval(tmp_path) -> None:
    approval = ApprovalGate(frozenset({"execute_tool"}))
    audit = ArchitectureAuditStore(tmp_path / "architecture.jsonl")
    runtime, capabilities, budget, _ = _runtime(approval=approval, audit=audit)
    action, context = _request()

    pending = runtime.execute(action, context)
    approval.decide(action.id, approved=True, decided_by="operator-1")
    executed = runtime.execute(action, context)
    replay = runtime.execute(action, context)

    assert pending.error == f"approval_pending:{action.id}"
    assert executed.success is True
    assert replay.error == f"approval_replay:{action.id}"
    assert len(capabilities.calls) == 1
    assert budget.actions_used == 1
    assert approval.requests[action.id].status is ApprovalStatus.CONSUMED
    assert audit.verify() is True


def test_rejected_approval_never_reaches_capability(tmp_path) -> None:
    approval = ApprovalGate(frozenset({"execute_tool"}))
    runtime, capabilities, budget, _ = _runtime(
        approval=approval,
        audit=ArchitectureAuditStore(tmp_path / "architecture.jsonl"),
    )
    action, context = _request()

    runtime.execute(action, context)
    approval.decide(action.id, approved=False, decided_by="operator-2")
    rejected = runtime.execute(action, context)

    assert rejected.error == "approval_rejected:operator-2"
    assert capabilities.calls == []
    assert budget.actions_used == 0


def test_audit_chain_detects_tampering(tmp_path) -> None:
    path = tmp_path / "architecture.jsonl"
    store = ArchitectureAuditStore(path)
    store.append("one", task_id="t1", action_id="a1", agent_id="agent", payload={"ok": True})
    store.append("two", task_id="t1", action_id="a1", agent_id="agent")

    assert store.verify() is True
    records = store.read()
    records[0]["payload"]["ok"] = False
    path.write_text("\n".join(json.dumps(item, sort_keys=True) for item in records) + "\n", encoding="utf-8")
    assert store.verify() is False


def test_audit_correlation_binds_task_and_action(tmp_path) -> None:
    store = ArchitectureAuditStore(tmp_path / "architecture.jsonl")
    action = Action("execute_tool", id="action-7")
    context = ExecutionContext("task-3", "agent-1")
    runtime, _, _, _ = _runtime(audit=store)

    assert runtime.execute(action, context).success is True

    assert {record["correlation_id"] for record in store.read()} == {"task-3:action-7"}
