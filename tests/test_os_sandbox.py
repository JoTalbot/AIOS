import sys

from aios_core.runtime.os_sandbox import OSSandboxBackend, OSSandboxPolicy


def test_os_sandbox_runs_with_restricted_environment():
    backend = OSSandboxBackend(OSSandboxPolicy(timeout_seconds=5, cpu_seconds=2))
    result = backend.run([sys.executable, "-c", "print('sandbox-ok')"])
    assert result.returncode == 0
    assert "sandbox-ok" in result.stdout


def test_os_sandbox_rejects_network_enabled_policy():
    backend = OSSandboxBackend(OSSandboxPolicy(network=True))
    try:
        backend.run([sys.executable, "-c", "pass"])
    except ValueError as exc:
        assert "isolated backend" in str(exc)
    else:
        raise AssertionError("network-enabled execution must require an isolated backend")
