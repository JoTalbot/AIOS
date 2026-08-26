"""Agent execution lifecycle manager."""

from enum import Enum


class ExecutionState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


class AgentExecutionManager:
    def __init__(self, event_bus=None, recovery_lifecycle=None):
        self.active = {}
        self.event_bus = event_bus
        self.recovery_lifecycle = recovery_lifecycle

    def _emit(self, name, payload):
        if self.event_bus:
            self.event_bus.publish(name, payload, source="agent_execution")

    def begin(self, execution_id, context):
        self.active[execution_id] = {
            "state": ExecutionState.RUNNING,
            "context": context,
            "error": None,
        }
        self._emit("execution.started", {"execution_id": execution_id})

    def complete(self, execution_id):
        execution = self.active.get(execution_id)
        if execution:
            execution["state"] = ExecutionState.COMPLETED
        self._emit("execution.completed", {"execution_id": execution_id})
        return execution

    def fail(self, execution_id, error=None):
        execution = self.active.get(execution_id)
        if execution:
            execution["state"] = ExecutionState.FAILED
            execution["error"] = error

        decision = None
        if self.recovery_lifecycle:
            if execution:
                execution["state"] = ExecutionState.RECOVERING
            decision = self.recovery_lifecycle.handle_failure(
                component="agent_execution",
                error=error,
                context={"execution_id": execution_id},
            )

        self._emit(
            "execution.failed",
            {"execution_id": execution_id, "error": error, "recovery": decision},
        )
        return execution

    def end(self, execution_id):
        return self.active.pop(execution_id, None)
