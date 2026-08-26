from execution.checkpoint import Checkpoint
from kernel.runtime_context import RuntimeContext
from kernel.runtime_persistence_facade import RuntimePersistenceFacade


class Adapter:
    def __init__(self):
        self.items = {}
        self.recoveries = []

    def save_checkpoint(self, checkpoint):
        self.items[checkpoint.task_id] = checkpoint
        return checkpoint

    def load_checkpoint(self, task_id):
        return self.items.get(task_id)

    def delete_checkpoint(self, task_id):
        self.items.pop(task_id, None)

    def record_recovery(self, event):
        self.recoveries.append(event)
        return event


def test_runtime_context_routes_checkpoint_and_recovery_to_facade():
    adapter = Adapter()
    facade = RuntimePersistenceFacade(adapter)
    context = RuntimeContext(persistence=facade)

    checkpoint = Checkpoint("task-1", {"step": 2})
    context.persistence_runtime.save_checkpoint(checkpoint)
    assert context.persistence_runtime.load_checkpoint("task-1") is checkpoint

    context.persistence_runtime.record_recovery({"action": "restore"})
    assert adapter.recoveries[0]["type"] == "recovery.decision"

    context.persistence_runtime.delete_checkpoint("task-1")
    assert context.persistence_runtime.load_checkpoint("task-1") is None
