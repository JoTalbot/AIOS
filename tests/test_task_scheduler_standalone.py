"""task_scheduler test."""
from aios_core.task_scheduler import TaskScheduler
def test_init(): s = TaskScheduler().stats(); assert isinstance(s, dict)
