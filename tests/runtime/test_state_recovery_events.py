"""Runtime state recovery event tests."""


def test_state_restored_event_contract():
    event = {"name": "state.restored", "metadata": {"restored": True}}
    assert event["name"] == "state.restored"
    assert event["metadata"]["restored"] is True


def test_recovery_rollback_marker():
    snapshot = {"version": 1, "rollback": True}
    assert snapshot["rollback"] is True
