from kernel.factory import KernelFactory


class Container:
    def __init__(self):
        self.services = {
            "kernel": object(), "agent_manager": object(), "bootstrap": object(),
            "planner": object(), "scheduler": object(), "agent": object(),
        }

    def list_services(self): return list(self.services)
    def has(self, name): return name in self.services
    def resolve(self, name): return self.services.get(name)


def test_factory_auto_wires_orchestrator_when_core_services_exist():
    context = KernelFactory(Container()).create_runtime()
    assert context.orchestrator is not None
    assert context.services()["orchestrator"] is context.orchestrator


def test_factory_leaves_orchestrator_unconfigured_when_services_are_missing():
    container = Container()
    del container.services["planner"]
    context = KernelFactory(container).create_runtime()
    assert context.orchestrator is None
