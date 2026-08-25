"""Build sandbox executors from a registered runtime backend."""
from __future__ import annotations

from typing import Callable

from .contracts import AgentResult, AgentStatus, AgentTask
from .docker_sandbox import DockerSandboxBackend
from .os_sandbox import OSSandboxBackend
from .sandbox import SandboxExecutor, SandboxPolicy
from .sandbox_registry import SandboxBackendRegistry


def build_default_sandbox_registry() -> SandboxBackendRegistry:
    registry = SandboxBackendRegistry()
    registry.register("os", OSSandboxBackend())
    registry.register("docker", DockerSandboxBackend())
    return registry


def select_backend(registry: SandboxBackendRegistry, name: str):
    """Resolve a configured backend and fail closed for unknown names."""
    return registry.get(name)


def build_sandbox_executor(
    registry: SandboxBackendRegistry,
    backend_name: str,
    policy: SandboxPolicy,
    command_handler: Callable[[AgentTask], AgentResult] | None = None,
) -> SandboxExecutor:
    """Create a SandboxExecutor bound to a selected concrete backend."""
    backend = select_backend(registry, backend_name)

    def run(task: AgentTask) -> AgentResult:
        if command_handler is not None:
            return command_handler(task)
        command = getattr(task, "command", None)
        if not command:
            return AgentResult(task_id=task.task_id, status=AgentStatus.BLOCKED, errors=("sandbox task has no command",), verdict="SANDBOX_BLOCKED")
        result = backend.run(list(command))
        if result.returncode != 0:
            return AgentResult(
                task_id=task.task_id,
                status=AgentStatus.FAILED,
                output=result.stdout,
                errors=(result.stderr or f"sandbox exit code {result.returncode}",),
                verdict="SANDBOX_FAILED",
            )
        return AgentResult(task_id=task.task_id, status=AgentStatus.COMPLETED, output=result.stdout, verdict="SANDBOX_OK")

    return SandboxExecutor(run, policy)
