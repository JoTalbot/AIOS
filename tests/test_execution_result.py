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
