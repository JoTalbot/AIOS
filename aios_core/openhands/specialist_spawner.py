"""OpenHands specialist conversation spawning with fail-closed validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SpecialistConversationClient(Protocol):
    def start_conversation(self, prompt: str, *, repository: str | None = None, branch: str | None = None, title: str | None = None, run: bool = True) -> dict: ...
    def wait_start_task(self, start_task_id: str, **kwargs) -> dict: ...
    def wait_execution(self, conversation_id: str, **kwargs) -> str: ...


@dataclass(frozen=True)
class SpawnedSpecialist:
    conversation_id: str
    start_task_id: str | None = None


class SpecialistSpawner:
    """Create and wait for an OpenHands specialist conversation."""

    def __init__(self, client: SpecialistConversationClient, repository: str | None = None):
        self._client = client
        self._repository = repository

    def spawn(self, *, role: str, task_id: str, title: str, description: str, changed_files: list[str], branch: str, reasons: tuple[str, ...] = ()) -> SpawnedSpecialist:
        prompt = (
            f"You are the {role} specialist for AIOS task {task_id}.\n\n"
            f"Title: {title}\n\nDescription:\n{description}\n\n"
            "Changed files:\n" + "\n".join(changed_files) + "\n\n"
            "Review only the requested specialist domain. Return an explicit "
            "APPROVED or CHANGES_REQUESTED verdict and concise evidence.\n"
            f"Escalation reasons: {', '.join(reasons) if reasons else 'policy-required'}"
        )
        result = self._client.start_conversation(prompt, repository=self._repository, branch=branch, title=f"{role}-review:{task_id}", run=True)
        conversation_id = str(result.get("conversation_id") or result.get("id") or "")
        if not conversation_id:
            raise RuntimeError("specialist spawn returned no conversation_id")
        start_task_id = result.get("start_task_id") or result.get("task_id")
        if start_task_id:
            self._client.wait_start_task(str(start_task_id))
        self._client.wait_execution(conversation_id)
        return SpawnedSpecialist(conversation_id=conversation_id, start_task_id=str(start_task_id) if start_task_id else None)
