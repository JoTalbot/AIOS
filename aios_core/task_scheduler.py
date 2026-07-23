"""Task Scheduler for AIOS"""

import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict


class TaskScheduler:
    """Simple in-memory task scheduler."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}

    def schedule(self, name: str, func: Callable, run_at: datetime, **kwargs) -> None:
        """Execute schedule."""
        self.tasks[name] = {
            "func": func,
            "run_at": run_at,
            "kwargs": kwargs,
            "status": "scheduled",
        }

    def schedule_in(self, name: str, func: Callable, seconds: int, **kwargs) -> None:
        """Execute schedule in."""
        run_at = datetime.now() + timedelta(seconds=seconds)
        self.schedule(name, func, run_at, **kwargs)

    def tick(self) -> None:
        """Execute tick."""
        now = datetime.now()
        for name, task in list(self.tasks.items()):
            if task["status"] == "scheduled" and now >= task["run_at"]:
                try:
                    task["func"](**task["kwargs"])
                    task["status"] = "completed"
                except Exception as e:
                    task["status"] = "failed"
                    task["error"] = str(e)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "total": len(self.tasks),
            "scheduled": sum(1 for t in self.tasks.values() if t["status"] == "scheduled"),
        }


scheduler = TaskScheduler()
