import asyncio

from execution.persistence import ExecutionStore
from kernel.factory import KernelFactory
from kernel.runtime_context import RuntimeContext


def test_runtime_context_recovery_is_initialized_once():
    class Bootstrap:
        pass

    class Container:
        def __init__(self):
            self.services = {
                "bootstrap": Bootstrap(),
                "kernel": type("Kernel", (), {})(),
                "agent_manager": object(),
                "persistence": ExecutionStore(),
                "scheduler": None,
            }

        def list_services(self):
            return list(self.services)

        def has(self, name):
            return name in self.services

        def resolve(self, name):
            return self.services[name]

    context = KernelFactory(Container()).create_runtime()
    assert isinstance(context, RuntimeContext)
    assert context.scheduler is None
    assert asyncio.run(context.recover()) == []
    assert context._recovery_initialized is True
    assert asyncio.run(context.recover()) == []
    assert context._recovery_initialized is True
