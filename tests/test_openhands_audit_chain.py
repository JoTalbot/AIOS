from aios_core.openhands.audit_chain import AuditChain


def test_audit_chain_links_events_and_verifies():
    chain = AuditChain()
    first = chain.append("e1", {"action": "start"})
    second = chain.append("e2", {"action": "gate", "decision": "PASS"})
    assert second.parent_event_id == first.event_id
    assert chain.verify()


def test_audit_chain_detects_tampering():
    chain = AuditChain()
    chain.append("e1", {"action": "start"})
    chain.append("e2", {"action": "gate", "decision": "PASS"})
    chain._events[1].payload["decision"] = "BLOCK"
    assert not chain.verify()
