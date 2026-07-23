"""Task scheduler operations tests."""
from aios_core.task_scheduler import TaskScheduler
def test_scheduler_ops():
    ts = TaskScheduler()
    assert ts.stats() is not None
