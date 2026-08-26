from execution.checkpoint_adapter import PersistenceCheckpointStore
from kernel.factory import KernelFactory


class ServiceContainer:
    def __init__(self):
        self.services = {
            "kernel": object(),
            "agent_manager": object(),
            "bootstrap": object(),
            "persistence": Persistence(),
            "scheduler": SchedulerStub(),
        }

    def list_services(self):
        return list(self.services)

    def has(self, name):
        return name in self.services

    def resolve(self, name):
        return self.services[name]


class Persistence:
    def __init__(self):
        self.items = {}

    def save_checkpoint(self, checkpoint):
        self.items[checkpoint.task_id] = checkpoint

    def load_checkpoint(self, task_id):
        return self.items.get(task_id)

    def delete_checkpoint(self, task_id):
        self.items.pop(task_id, None)


class SchedulerStub:
    checkpoint_store = None


def test_factory_wires_persistence_checkpoint_store():
    container = ServiceContainer()
    context = KernelFactory(container).create_runtime()
    assert isinstance(container.services["scheduler"].checkpoint_store, PersistenceCheckpointStore)
    assert context.persistence.adapter is container.services["persistence"]
