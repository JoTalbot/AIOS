from dataclasses import dataclass


@dataclass
class RuntimeExecution:
    task_id: str
    result: object


class MainRuntimeIntegration:
    """Integration point between core runtime and multi-agent orchestration."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    def execute(self, task_id: str, payload=None):
        if self.orchestrator:
            result = self.orchestrator.run(task_id, payload)
        else:
            result = payload

        return RuntimeExecution(
            task_id=task_id,
            result=result,
        )
