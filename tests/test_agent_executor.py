from aios_core.runtime.contracts import AgentResult, AgentStatus, AgentTask
from aios_core.runtime.executor import AgentExecutor


def test_executor_completes_successful_task():
    def handler(task):
        return AgentResult(task_id=task.task_id, status=AgentStatus.COMPLETED, output="ok")

    record = AgentExecutor(handler).execute(AgentTask(id="t1", goal="test"))
    assert record.status is AgentStatus.COMPLETED
    assert record.result.output == "ok"


def test_executor_converts_handler_exception_to_failure():
    def handler(task):
        raise RuntimeError("boom")

    record = AgentExecutor(handler).execute(AgentTask(id="t2", goal="test"))
    assert record.status is AgentStatus.FAILED
    assert "RuntimeError: boom" in record.result.errors[0]


def test_executor_rejects_terminal_task():
    task = AgentTask(id="t3", goal="test", status=AgentStatus.COMPLETED)
    try:
        AgentExecutor(lambda _: None).execute(task)
    except ValueError as exc:
        assert "not executable" in str(exc)
    else:
        raise AssertionError("terminal task must not execute")
