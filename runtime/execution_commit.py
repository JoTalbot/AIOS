"""Crash-recoverable execution commit protocol with durable journal status."""

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
    status: str = "pending"


class ExecutionCommitCoordinator:
    """Durable journal with explicit pending/applied/reconciled status and safe replay."""

    def __init__(self, store: ExecutionStore, audit_log: ExecutionAuditLog, journal_path: str = "data/execution_commits.jsonl"):
        self.store = store
        self.audit_log = audit_log
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_journal(self, commit: ExecutionCommit):
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(commit), ensure_ascii=False, default=str) + "\n")
            handle.flush()

    def _rewrite(self, commits):
        tmp = self.journal_path.with_suffix(self.journal_path.suffix + ".tmp")
        tmp.write_text("".join(json.dumps(asdict(c), ensure_ascii=False, default=str) + "\n" for c in commits), encoding="utf-8")
        tmp.replace(self.journal_path)

    def commit(self, state: ExecutionState, to_status: str, *, checkpoint=None, reason=None):
        current = self.store.get(state.execution_id) or state
        commit_id = f"{current.execution_id}:{current.attempt}:{to_status}:{current.correlation_id or ''}"
        existing = {c.commit_id: c for c in self.pending(all_statuses=True)}.get(commit_id)
        if existing:
            return existing
        commit = ExecutionCommit(commit_id, current.execution_id, current.status, to_status, current.attempt, checkpoint, reason, correlation_id=current.correlation_id)
        self._append_journal(commit)
        self.store.transition(current.execution_id, to_status,
                              result=checkpoint if to_status == "completed" else current.result,
                              error=reason if to_status == "failed" else current.error)
        self.audit_log.append(ExecutionAuditEvent(current.execution_id, current.status, to_status, current.attempt, reason,
                                                  correlation_id=current.correlation_id, event_id=commit_id))
        self._mark(commit_id, "applied")
        return commit

    def _mark(self, commit_id: str, status: str):
        commits = self.pending(all_statuses=True)
        for i, commit in enumerate(commits):
            if commit.commit_id == commit_id:
                commits[i] = ExecutionCommit(**{**asdict(commit), "status": status})
                break
        self._rewrite(commits)

    def reconcile(self):
        repaired = []
        for commit in self.pending():
            state = self.store.get(commit.execution_id)
            if not state:
                continue
            if state.status == commit.to_status:
                self.audit_log.append(ExecutionAuditEvent(commit.execution_id, commit.from_status, commit.to_status,
                                                          commit.attempt, commit.reason, correlation_id=commit.correlation_id,
                                                          event_id=commit.commit_id))
                self._mark(commit.commit_id, "reconciled")
                repaired.append(commit.commit_id)
                continue
            if state.status != commit.from_status:
                continue
            self.store.transition(commit.execution_id, commit.to_status,
                                  result=commit.checkpoint if commit.to_status == "completed" else state.result,
                                  error=commit.reason if commit.to_status == "failed" else state.error)
            self.audit_log.append(ExecutionAuditEvent(commit.execution_id, commit.from_status, commit.to_status,
                                                      commit.attempt, commit.reason, correlation_id=commit.correlation_id,
                                                      event_id=commit.commit_id))
            self._mark(commit.commit_id, "reconciled")
            repaired.append(commit.commit_id)
        return repaired

    def pending(self, all_statuses=False):
        if not self.journal_path.exists():
            return []
        result = []
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            raw.setdefault("status", "pending")
            commit = ExecutionCommit(**raw)
            if all_statuses or commit.status == "pending":
                result.append(commit)
        return result
