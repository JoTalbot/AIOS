from execution.checkpoint import Checkpoint
from kernel.runtime_persistence_facade import RuntimePersistenceFacade


class Adapter:
    def __init__(self):
        self.checkpoints = {}
        self.events = []

    def save_checkpoint(self, checkpoint):
        self.checkpoints[checkpoint.task_id] = checkpoint
        return checkpoint

    def load_checkpoint(self, task_id):
        return self.checkpoints.get(task_id)

    def delete_checkpoint(self, task_id):
        self.checkpoints.pop(task_id, None)

    def record(self, event):
        self.events.append(event)
        return event

    def record_recovery(self, event):
        return self.record(event)


def test_facade_routes_checkpoint_and_recovery_to_one_adapter():
    adapter = Adapter()
    facade = RuntimePersistenceFacade(adapter)
    checkpoint = Checkpoint("task-1", {"step": 2})

    assert facade.save_checkpoint(checkpoint) is checkpoint
    assert facade.load_checkpoint("task-1") is checkpoint
    facade.record_recovery({"action": "restore"})
    assert adapter.events[-1]["action"] == "restore"
    facade.delete_checkpoint("task-1")
    assert facade.load_checkpoint("task-1") is None
