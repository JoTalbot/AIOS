from aios_core.runtime.docker_sandbox import DockerSandboxBackend, DockerSandboxPolicy


def test_docker_backend_has_conservative_defaults():
    policy = DockerSandboxPolicy()
    assert policy.network is False
    assert policy.read_only_root is True
    assert policy.pids_limit > 0
    assert policy.memory


def test_docker_backend_rejects_invalid_command():
    backend = DockerSandboxBackend()
    try:
        backend.run([])
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:
        raise AssertionError("empty command must be rejected")
