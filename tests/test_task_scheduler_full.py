"""Task scheduler full."""
from aios_core.task_scheduler import TaskScheduler
def test(): s=TaskScheduler().stats(); assert isinstance(s,dict)
