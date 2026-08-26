from execution import ExecutionResult


def test_success_result_contract():
    result = ExecutionResult.success("task-1", value={"ok": True})
    assert result.ok
    assert result.status == "completed"
    assert result.value == {"ok": True}
    assert result.error is None


def test_failure_result_contract():
    result = ExecutionResult.failure("task-2", RuntimeError("boom"))
    assert not result.ok
    assert result.status == "failed"
    assert result.error == "boom"


def test_result_metadata_isolated_from_input():
    metadata = {"attempt": 2}
    result = ExecutionResult.success("task-3", metadata=metadata)
    metadata["attempt"] = 99
    assert result.metadata == {"attempt": 2}
