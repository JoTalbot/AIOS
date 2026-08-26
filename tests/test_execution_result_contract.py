from execution import ExecutionResult


def test_execution_result_has_stable_wire_contract():
    result = ExecutionResult.success("task-1", value={"answer": 42}, metadata={"source": "tool"})
    payload = result.to_dict()
    event_payload = result.to_event_payload()

    assert payload == {
        "task_id": "task-1",
        "status": "completed",
        "value": {"answer": 42},
        "error": None,
        "metadata": {"source": "tool"},
    }
    assert event_payload == payload
    assert ExecutionResult.failure("task-2", ValueError("boom")).to_dict()["error"] == "boom"
