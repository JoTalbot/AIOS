"""Docker-backed sandbox for already-approved agent commands.

Requires a local Docker daemon. This backend deliberately uses conservative
flags and never enables network access unless explicitly requested by policy.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DockerSandboxPolicy:
    image: str = "python:3.12-slim"
    timeout_seconds: int = 60
    memory: str = "512m"
    cpus: str = "1.0"
    pids_limit: int = 64
    network: bool = False
    read_only_root: bool = True


class DockerSandboxBackend:
    """Run a command in a short-lived, resource-limited Docker container."""

    def __init__(self, policy: DockerSandboxPolicy | None = None) -> None:
        self.policy = policy or DockerSandboxPolicy()

    def run(self, command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if not command or any(not isinstance(item, str) or not item for item in command):
            raise ValueError("command must be a non-empty list of strings")
        p = self.policy
        if p.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        args = [
            "docker", "run", "--rm", "--init",
            "--memory", p.memory,
            "--cpus", p.cpus,
            "--pids-limit", str(p.pids_limit),
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
        ]
        if p.read_only_root:
            args += ["--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m"]
        args += ["--network", "none" if not p.network else "bridge"]
        for key, value in (env or {}).items():
            args += ["--env", f"{key}={value}"]
        args += [p.image, *command]
        return subprocess.run(args, text=True, capture_output=True, timeout=p.timeout_seconds, check=False)
