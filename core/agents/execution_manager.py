"""Agent execution lifecycle manager."""

from enum import Enum


class ExecutionState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentExecutionManager:
    def __init__(self):
        self.active = {}

    def begin(self, execution_id, context):
        self.active[execution_id] = {
            "state": ExecutionState.RUNNING,
            "context": context,
        }
        return self.active[execution_id]

    def complete(self, execution_id):
        execution = self.active.get(execution_id)
        if execution:
            execution["state"] = ExecutionState.COMPLETED
        return execution

    def fail(self, execution_id, error=None):
        execution = self.active.get(execution_id)
        if execution:
            execution["state"] = ExecutionState.FAILED
            execution["error"] = error
        return execution

    def end(self, execution_id):
        return self.active.pop(execution_id, None)
