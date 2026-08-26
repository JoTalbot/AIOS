"""Crash-recoverable execution commit protocol for state + audit + checkpoint metadata."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional

from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_store import ExecutionState, ExecutionStore


@dataclass(frozen=True)
class ExecutionCommit:
    commit_id: str
    execution_id: str
    from_status: str
    to_status: str
    attempt: int
    checkpoint: Any = None
    reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None


class ExecutionCommitCoordinator:
    """Uses a durable commit journal so startup can reconcile interrupted commits."""

    def __init__(self, store: ExecutionStore, audit_log: ExecutionAuditLog, journal_path: str = "data/execution_commits.jsonl"):
        self.store = store
        self.audit_log = audit_log
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_journal(self, commit: ExecutionCommit):
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(commit), ensure_ascii=False, default=str) + "\n")
            handle.flush()

    def commit(self, state: ExecutionState, to_status: str, *, checkpoint=None, reason=None):
        current = self.store.get(state.execution_id) or state
        commit_id = f"{current.execution_id}:{current.attempt}:{to_status}:{current.correlation_id or ''}"
        commit = ExecutionCommit(commit_id, current.execution_id, current.status, to_status, current.attempt, checkpoint, reason, correlation_id=current.correlation_id)
        self._append_journal(commit)
        self.store.transition(current.execution_id, to_status, result=checkpoint if to_status == "completed" else current.result, error=reason if to_status == "failed" else current.error)
        self.audit_log.append(ExecutionAuditEvent(current.execution_id, current.status, to_status, current.attempt, reason, correlation_id=current.correlation_id))
        return commit

    def pending(self):
        if not self.journal_path.exists():
            return []
        return [ExecutionCommit(**json.loads(line)) for line in self.journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
