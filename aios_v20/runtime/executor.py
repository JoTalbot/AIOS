from dataclasses import dataclass


@dataclass
class ExecutionResult:
    status: str
    output: object | None = None
    error: str | None = None


class RuntimeExecutor:
    """Controlled execution layer for AIOS v20."""

    def execute(self, task, constraints=None):
        try:
            return ExecutionResult(
                status="COMPLETED",
                output={"task": task, "constraints": constraints},
            )
        except Exception as exc:
            return ExecutionResult(
                status="FAILED",
                error=str(exc),
            )
