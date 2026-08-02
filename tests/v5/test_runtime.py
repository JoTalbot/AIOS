from aios_core.v5.runtime.context import ExecutionContext


def test_execution_context():
    ctx = ExecutionContext(task_id="test")
    assert ctx.task_id == "test"
