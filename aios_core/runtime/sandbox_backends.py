"""Pluggable sandbox backend contract for AIOS."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SandboxRequest:
    command: tuple[str, ...]
    workdir: str | None = None
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


class SandboxBackend(Protocol):
    """Backend interface for OS/container/VM sandbox implementations."""

    def run(self, request: SandboxRequest) -> SandboxResult: ...
