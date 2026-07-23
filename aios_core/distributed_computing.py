"""Distributed Computing Framework for AIOS"""

from typing import Dict, List, Callable, Any


class DistributedTask:
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = "pending"
        self.result = None


class DistributedComputing:
    """Simple distributed task execution."""

    def __init__(self):
        self.workers: Dict[str, Dict] = {}
        self.tasks: Dict[str, DistributedTask] = {}

    def register_worker(self, worker_id: str, capabilities: List[str]):
        self.workers[worker_id] = {"capabilities": capabilities, "status": "idle"}

    def submit(self, func: Callable, *args, **kwargs) -> str:
        task_id = f"task_{len(self.tasks)}"
        task = DistributedTask(task_id, func, args, kwargs)
        self.tasks[task_id] = task
        return task_id

    def get_result(self, task_id: str) -> Any:
        task = self.tasks.get(task_id)
        return task.result if task else None

    def stats(self) -> dict:
        return {"workers": len(self.workers), "tasks": len(self.tasks)}
