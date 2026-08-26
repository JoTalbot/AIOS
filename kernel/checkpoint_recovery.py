"""Restore persisted execution checkpoints into a newly created Scheduler."""

from kernel.scheduler import AgentTask, TaskState


class CheckpointRecovery:
    def __init__(self, checkpoint_store):
        self.store = checkpoint_store

    async def restore(self, scheduler):
        if self.store is None or not hasattr(self.store, "_items"):
            return []
        restored = []
        for task_id, checkpoint in list(self.store._items.items()):
            payload = dict(checkpoint.payload)
            task_payload = dict(payload.get("task_payload", payload))
            # Completed checkpoints are terminal and must never be replayed.
            if task_payload.get("result") is not None:
                continue
            task = AgentTask(task_id, task_payload.get("agent", "unknown"), task_payload)
            task.attempts = checkpoint.attempt
            task.checkpoint = payload
            task.state = TaskState.RESTORING
            scheduler.tasks[task_id] = task
            await scheduler.queue.put(task)
            restored.append(task)
        return restored
