"""AIOS Result Store.
Stores execution results from agents.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoredResult:
    task_id: str
    status: str
    output: object = None
    created_at: str = ""


class ResultStore:
    def __init__(self):
        self.results = {}

    def save(self, result: StoredResult):
        if not result.created_at:
            result.created_at = datetime.utcnow().isoformat()
        self.results[result.task_id] = result
        return result

    def get(self, task_id: str):
        return self.results.get(task_id)
