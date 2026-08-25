from aios_core.openhands.audit_chain import AuditChain


def test_checkpoint_records_root_and_sequence():
    chain = AuditChain()
    chain.append("e1", {"action": "start"})
    checkpoint = chain.checkpoint()
    assert checkpoint.sequence == 1
    assert checkpoint.last_event_id == "e1"
    assert checkpoint.root_hash == chain.events[-1].event_hash
    assert chain.verify()


def test_checkpoint_detects_truncation():
    chain = AuditChain()
    chain.append("e1", {"action": "start"})
    chain.checkpoint()
    chain.append("e2", {"action": "gate"})
    chain._events.pop(0)
    assert not chain.verify()
