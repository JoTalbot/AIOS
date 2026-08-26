from core.runtime.execution_context import ExecutionContext


def test_execution_context_events():
    ctx = ExecutionContext('test')
    ctx.add_event('started')
    assert ctx.events == ['started']
