"""AIOS Agent Executor.

Execution layer connecting validated tasks with agents.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionResult:
    task_id: str
    status: str
    output: object = None
    error: str | None = None
    timestamp: str = ""


class AgentExecutor:
    def __init__(self, registry=None, permission_engine=None):
        self.registry = registry
        self.permission_engine = permission_engine

    async def execute(self, task):
        agent = None
        if self.registry:
            agent = self.registry.get(task.agent_id)

        if agent is None:
            return ExecutionResult(
                task_id=task.id,
                status="failed",
                error="agent_not_found",
                timestamp=datetime.utcnow().isoformat(),
            )

        if self.permission_engine and not self.permission_engine.check(agent.id, task.action):
            return ExecutionResult(
                task_id=task.id,
                status="denied",
                error="permission_denied",
                timestamp=datetime.utcnow().isoformat(),
            )

        try:
            result = await agent.execute(task)
            return ExecutionResult(
                task_id=task.id,
                status="completed",
                output=result,
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as exc:
            return ExecutionResult(
                task_id=task.id,
                status="failed",
                error=str(exc),
                timestamp=datetime.utcnow().isoformat(),
            )
