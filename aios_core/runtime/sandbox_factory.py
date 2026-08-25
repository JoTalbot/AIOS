"""Factory for selecting a registered sandbox backend from runtime configuration."""
from __future__ import annotations

from .docker_sandbox import DockerSandboxBackend, DockerSandboxPolicy
from .os_sandbox import OSSandboxBackend, OSSandboxPolicy
from .sandbox_registry import SandboxBackendRegistry


def build_default_sandbox_registry() -> SandboxBackendRegistry:
    registry = SandboxBackendRegistry()
    registry.register("os", OSSandboxBackend())
    registry.register("docker", DockerSandboxBackend())
    return registry


def select_backend(registry: SandboxBackendRegistry, name: str):
    """Resolve a configured backend and fail closed for unknown names."""
    return registry.get(name)
