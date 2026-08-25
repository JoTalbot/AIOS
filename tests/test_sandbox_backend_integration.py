from aios_core.runtime.sandbox_factory import build_default_sandbox_registry, select_backend
from aios_core.runtime.sandbox_registry import SandboxBackendRegistry


class FakeBackend:
    def __init__(self):
        self.calls = []

    def run(self, command, *, env=None):
        self.calls.append((command, env))
        return type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()


def test_registry_dispatches_to_registered_backend():
    registry = SandboxBackendRegistry()
    backend = FakeBackend()
    registry.register("fake", backend)

    resolved = select_backend(registry, "fake")
    result = resolved.run(["python", "-c", "print('ok')"])

    assert result.returncode == 0
    assert backend.calls == [(["python", "-c", "print('ok')"], None)]


def test_default_registry_exposes_real_backends():
    registry = build_default_sandbox_registry()
    assert set(registry.names()) == {"docker", "os"}
    assert select_backend(registry, "docker") is not None
    assert select_backend(registry, "os") is not None
