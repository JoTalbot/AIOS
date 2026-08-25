from aios_core.runtime.sandbox_factory import build_default_sandbox_registry, select_backend
from aios_core.runtime.docker_sandbox import DockerSandboxBackend
from aios_core.runtime.os_sandbox import OSSandboxBackend


def test_default_registry_contains_os_and_docker():
    registry = build_default_sandbox_registry()
    assert registry.names() == ("docker", "os")
    assert isinstance(select_backend(registry, "docker"), DockerSandboxBackend)
    assert isinstance(select_backend(registry, "os"), OSSandboxBackend)


def test_unknown_backend_fails_closed():
    registry = build_default_sandbox_registry()
    try:
        select_backend(registry, "unknown")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown sandbox backend must fail closed")
