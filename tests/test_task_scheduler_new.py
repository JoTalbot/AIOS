"""task_scheduler test."""
def test(): from aios_core.task_scheduler import TaskScheduler; s = TaskScheduler().stats(); assert isinstance(s, dict)
