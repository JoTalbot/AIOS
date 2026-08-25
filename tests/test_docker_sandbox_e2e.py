import shutil
import subprocess
import sys

import pytest

from aios_core.runtime.docker_sandbox import DockerSandboxBackend, DockerSandboxPolicy


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.mark.skipif(not _docker_available(), reason="Docker daemon is unavailable")
def test_real_docker_sandbox_executes_isolated_command():
    backend = DockerSandboxBackend(DockerSandboxPolicy(timeout_seconds=30, memory="128m", cpus="0.5", pids_limit=16))
    result = backend.run([sys.executable, "-c", "print('aios-docker-e2e')"])
    assert result.returncode == 0
    assert result.stdout.strip() == "aios-docker-e2e"


@pytest.mark.skipif(not _docker_available(), reason="Docker daemon is unavailable")
def test_real_docker_sandbox_has_no_network_by_default():
    backend = DockerSandboxBackend(DockerSandboxPolicy(timeout_seconds=30))
    result = backend.run([sys.executable, "-c", "import socket; socket.create_connection(('example.com', 80), 2)"])
    assert result.returncode != 0
