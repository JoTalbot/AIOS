from __future__ import annotations

import pytest

from aios_core.kernel import (
    AgentIdentity,
    AuditLogger,
    ExecutionContext,
    IdentityRegistry,
    Kernel,
    PolicyEngine,
    TrustManager,
)
from aios_core.kernel.exceptions import UnknownIdentity


def _kernel(*, capabilities=("execute_tool",), trust="T1", min_trust="T1"):
    identity = AgentIdentity("agent-1", "developer", capabilities)
    identities = IdentityRegistry((identity,))
    trust_manager = TrustManager()
    trust_manager.grant(identity.agent_id, trust)
    policy = PolicyEngine()
    policy.allow("execute_tool", min_trust)
    audit = AuditLogger()
    return Kernel(identities, trust_manager, policy, audit), audit


def test_kernel_allows_and_audits_complete_decision_context() -> None:
    kernel, audit = _kernel()

    decision = kernel.process(ExecutionContext("agent-1", "execute_tool"))

    assert decision.allowed is True
    assert decision.reason == "allowed"
    assert audit.get_events()[0] | {"timestamp": "ignored"} == {
        "allowed": True,
        "reason": "allowed",
        "agent_id": "agent-1",
        "capability": "execute_tool",
        "trust_level": "T1",
        "timestamp": "ignored",
    }
    assert audit.get_events()[0]["timestamp"].endswith("+00:00")


def test_kernel_denies_insufficient_trust_and_audits_denial() -> None:
    kernel, audit = _kernel(trust="T0", min_trust="T2")

    decision = kernel.process(ExecutionContext("agent-1", "execute_tool"))

    assert decision.allowed is False
    assert decision.reason == "insufficient_trust"
    assert audit.get_events()[0]["allowed"] is False


def test_kernel_denies_capability_missing_from_identity() -> None:
    kernel, _ = _kernel(capabilities=())

    decision = kernel.process(ExecutionContext("agent-1", "execute_tool"))

    assert decision.allowed is False
    assert decision.reason == "identity_missing_capability"


def test_kernel_rejects_unknown_identity_before_policy_evaluation() -> None:
    kernel, audit = _kernel()

    with pytest.raises(UnknownIdentity, match="unknown agent identity"):
        kernel.process(ExecutionContext("intruder", "execute_tool"))

    assert audit.get_events() == []


def test_audit_logger_does_not_mutate_input_or_expose_internal_state() -> None:
    audit = AuditLogger()
    source = {"allowed": False}

    audit.record(source)
    returned = audit.get_events()
    returned[0]["allowed"] = True

    assert source == {"allowed": False}
    assert audit.get_events()[0]["allowed"] is False
