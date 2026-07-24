"""Simple Distributed Task Queue for AIOS"""

import json
import os
from typing import Any, Dict, List, Optional


class DistributedQueue:
    """File-based distributed task queue (simple implementation)."""

    def __init__(self, queue_dir: str = "queue"):
        """Initialize DistributedQueue."""
        self.queue_dir = queue_dir
        os.makedirs(queue_dir, exist_ok=True)

    def enqueue(self, task: dict[str, Any]) -> str:
        """Execute enqueue."""
        task_id = task.get("id") or str(hash(json.dumps(task)))
        filepath = os.path.join(self.queue_dir, f"{task_id}.json")
        with open(filepath, "w") as f:
            json.dump(task, f)
        return task_id

    def dequeue(self) -> dict[str, Any] | None:
        """Execute dequeue."""
        files = sorted(os.listdir(self.queue_dir))
        if not files:
            return None
        filepath = os.path.join(self.queue_dir, files[0])
        with open(filepath) as f:
            task = json.load(f)
        os.remove(filepath)
        return task

    def size(self) -> int:
        """Execute size."""
        return len(os.listdir(self.queue_dir))

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"queue_size": self.size(), "queue_dir": self.queue_dir}
