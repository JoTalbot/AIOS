from aios_core.runtime.sandbox_registry import SandboxBackendRegistry


class FakeBackend:
    def run(self, command, *, env=None):
        return command


def test_registry_registers_and_resolves_backend():
    registry = SandboxBackendRegistry()
    backend = FakeBackend()
    registry.register("docker", backend)
    assert registry.get("docker") is backend
    assert registry.names() == ("docker",)


def test_registry_rejects_unknown_backend():
    registry = SandboxBackendRegistry()
    try:
        registry.get("missing")
    except KeyError as exc:
        assert "not registered" in str(exc)
    else:
        raise AssertionError("unknown backend must fail closed")
