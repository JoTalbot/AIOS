from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aios_core.architecture.approval import ApprovalGate
from aios_core.architecture.approval_transport import ApprovalCommand, ApprovalCommandVerifier
from aios_core.architecture.audit import ArchitectureAuditStore
from aios_core.architecture.audit_tools import AuditQuery
from aios_core.architecture.capabilities import CapabilityDefinition, CapabilityRegistry
from aios_core.architecture.delegation import DelegationRegistry
from aios_core.architecture.delegation_chain import DelegationChainValidator
from aios_core.architecture.health import architecture_health
from aios_core.architecture.idempotency import IdempotencyLedger
from aios_core.architecture.risk import controls_for
from aios_core.architecture.security_profile import ArchitectureSecurityProfile
from aios_core.architecture.signing import HMACSigner


def test_signed_approval_rejects_replay_and_stale_commands() -> None:
    signer = HMACSigner(b"k" * 32, "operator-key")
    gate = ApprovalGate(frozenset({"deploy"}))
    gate.request(action_id="a1", task_id="t1", agent_id="agent", capability="deploy")
    now = datetime.now(UTC)
    unsigned = ApprovalCommand("a1", True, "owner", now.isoformat(), "nonce-1", signer.key_id)
    command = ApprovalCommand(**(unsigned.payload() | {"signature": signer.sign(unsigned.payload())}))
    verifier = ApprovalCommandVerifier({signer.key_id: signer})

    assert verifier.apply(command, gate, now=now).decided_by == "owner"
    with pytest.raises(RuntimeError, match="replayed"):
        verifier.apply(command, gate, now=now)


def test_delegation_chain_must_attenuate_scope_and_lifetime() -> None:
    signer = HMACSigner(b"d" * 32, "delegation-key")
    registry = DelegationRegistry({signer.key_id: signer})
    expiry = datetime.now(UTC) + timedelta(minutes=5)
    parent = registry.issue(
        owner_id="owner", delegated_by="root", task_id="t", role="parent",
        agent_id="parent", capabilities=frozenset({"read", "write"}), expires_at=expiry,
        key_id=signer.key_id,
    )
    child = registry.issue(
        owner_id="owner", delegated_by="parent", task_id="t", role="child",
        agent_id="child", capabilities=frozenset({"read"}),
        expires_at=expiry - timedelta(minutes=1), key_id=signer.key_id,
    )
    registry.validate(parent.grant_id, task_id="t", role="parent", agent_id="parent", capability="read")
    DelegationChainValidator().validate((parent, child))
    child.capabilities = frozenset({"read", "delete"})
    with pytest.raises(RuntimeError, match="expanded"):
        DelegationChainValidator().validate((parent, child))


def test_idempotency_registry_risk_audit_and_health(tmp_path) -> None:
    ledger = IdempotencyLedger()
    assert ledger.record("k1", "fp", {"ok": True}).result == {"ok": True}
    with pytest.raises(RuntimeError, match="different request"):
        ledger.record("k1", "other", None)

    registry = CapabilityRegistry()
    definition = CapabilityDefinition("deploy", "platform", "critical")
    registry.register(definition)
    assert controls_for(registry.require("deploy")).max_delegation_seconds == 60
    profile = ArchitectureSecurityProfile.build((definition,))
    assert profile.approval.requires("deploy") is True

    store = ArchitectureAuditStore(tmp_path / "audit.jsonl")
    store.append("execution_denied", task_id="t", action_id="a", agent_id="agent")
    assert len(AuditQuery(store).find(correlation_id="t:a")) == 1
    assert architecture_health(audit=store, approval=None, delegations=None).healthy is True
