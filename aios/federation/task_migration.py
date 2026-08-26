"""Task migration layer for federation nodes."""

from dataclasses import dataclass


@dataclass
class MigrationRequest:
    task_id: str
    source: str
    destination: str


class TaskMigration:
    def migrate(self, request: MigrationRequest):
        return {"task_id": request.task_id, "migrated": True}
