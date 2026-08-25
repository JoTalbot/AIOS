"""Optional OS-level subprocess sandbox backend.

This backend is intentionally conservative: it runs a supplied command with a
minimal environment, resource limits and an isolated working directory. It is
not a container or VM and must not be treated as a complete security boundary.
"""
from __future__ import annotations

import os
import resource
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class OSSandboxPolicy:
    timeout_seconds: int = 60
    cpu_seconds: int = 30
    memory_bytes: int = 512 * 1024 * 1024
    max_processes: int = 32
    network: bool = False


class OSSandboxBackend:
    """Execute an already-approved command with conservative OS limits."""

    def __init__(self, policy: OSSandboxPolicy | None = None) -> None:
        self.policy = policy or OSSandboxPolicy()

    def _limits(self) -> None:
        p = self.policy
        resource.setrlimit(resource.RLIMIT_CPU, (p.cpu_seconds, p.cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (p.memory_bytes, p.memory_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (p.max_processes, p.max_processes))

    def run(self, command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if not command or any(not isinstance(item, str) or not item for item in command):
            raise ValueError("command must be a non-empty list of strings")
        if self.policy.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.policy.network:
            raise ValueError("network-enabled execution requires an explicit isolated backend")

        workdir = tempfile.mkdtemp(prefix="aios-sandbox-")
        safe_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": workdir}
        if env:
            safe_env.update({str(k): str(v) for k, v in env.items()})
        return subprocess.run(
            command,
            cwd=workdir,
            env=safe_env,
            text=True,
            capture_output=True,
            timeout=self.policy.timeout_seconds,
            preexec_fn=self._limits,
            check=False,
        )
