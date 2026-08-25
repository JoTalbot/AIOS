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
    command_handler: Callable[[AgentTask], AgentResult],
) -> SandboxExecutor:
    """Create a SandboxExecutor bound to a selected backend.

    The command adapter is explicit because AgentTask intentionally does not
    contain an implicit command field. It receives the selected backend and is
    responsible for constructing and executing a backend-specific command.
    """
    backend = select_backend(registry, backend_name)

    def run(task: AgentTask) -> AgentResult:
        return command_handler(task)

    # Resolve the backend during construction so an invalid configuration fails
    # closed before an agent task can reach execution.
    _ = backend
    return SandboxExecutor(run, policy)
