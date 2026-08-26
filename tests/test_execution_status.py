from execution import (
    EXECUTION_COMPLETED_STATUS,
    EXECUTION_FAILED_STATUS,
    TERMINAL_EXECUTION_STATUSES,
    is_terminal_status,
)


def test_status_contract_is_canonical():
    assert EXECUTION_COMPLETED_STATUS == "completed"
    assert EXECUTION_FAILED_STATUS == "failed"
    assert TERMINAL_EXECUTION_STATUSES == frozenset({"completed", "failed"})
    assert is_terminal_status("completed")
    assert is_terminal_status("failed")
    assert not is_terminal_status("running")
