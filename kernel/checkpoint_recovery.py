"""Restore persisted execution checkpoints into a newly created Scheduler."""

from kernel.scheduler import AgentTask, TaskState


class CheckpointRecovery:
    def __init__(self, checkpoint_store, persistence=None):
        self.store = checkpoint_store
        self.persistence = persistence

    @staticmethod
    def _valid(checkpoint):
        return (
            checkpoint is not None
            and isinstance(getattr(checkpoint, "task_id", None), str)
            and bool(checkpoint.task_id)
            and isinstance(getattr(checkpoint, "payload", None), dict)
            and isinstance(getattr(checkpoint, "attempt", 0), int)
            and checkpoint.attempt >= 0
        )

    def _already_completed(self, task_id):
        return self.persistence is not None and self.persistence.load_result(task_id) is not None

    async def restore(self, scheduler):
        if self.store is None or not hasattr(self.store, "_items"):
            return []
        restored = []
        for task_id, checkpoint in list(self.store._items.items()):
            if task_id in scheduler.tasks or self._already_completed(task_id) or not self._valid(checkpoint):
                continue
            payload = dict(checkpoint.payload)
            task_payload = payload.get("task_payload", payload)
            if not isinstance(task_payload, dict) or task_payload.get("result") is not None:
                continue
            agent = task_payload.get("agent", "unknown")
            if not isinstance(agent, str) or not agent:
                continue
            task = AgentTask(task_id, agent, dict(task_payload))
            task.attempts = checkpoint.attempt
            task.checkpoint = payload
            task.state = TaskState.RESTORING
            scheduler.tasks[task_id] = task
            await scheduler.queue.put(task)
            restored.append(task)
        return restored
