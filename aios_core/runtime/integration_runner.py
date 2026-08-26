"""AIOS Runtime Integration Runner

First executable integration layer connecting runtime components.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ExecutionResult:
    task_id: str
    status: str
    output: object
    timestamp: str


class IntegrationRunner:
    def __init__(self, runtime=None, registry=None):
        self.runtime = runtime
        self.registry = registry

    async def execute(self, agent_id: str, task):
        if self.registry:
            agent = self.registry.get(agent_id)
            if agent is None:
                return ExecutionResult(
                    task_id=str(task),
                    status="agent_not_found",
                    output=None,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        return ExecutionResult(
            task_id=str(task),
            status="completed",
            output=task,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
