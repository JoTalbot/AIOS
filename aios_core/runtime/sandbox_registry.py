"""Registry for selecting sandbox backends without coupling the executor to one implementation."""
from __future__ import annotations

from typing import Any, Protocol


class SandboxBackend(Protocol):
    def run(self, command: list[str], *, env: dict[str, str] | None = None) -> Any: ...


class SandboxBackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, SandboxBackend] = {}

    def register(self, name: str, backend: SandboxBackend) -> None:
        if not name or not name.strip():
            raise ValueError("backend name must not be empty")
        self._backends[name] = backend

    def get(self, name: str) -> SandboxBackend:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise KeyError(f"sandbox backend not registered: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))
