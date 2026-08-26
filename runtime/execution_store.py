"""Persistent execution state with an explicit, validated lifecycle."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional


class InvalidExecutionTransition(ValueError):
    pass


@dataclass
class ExecutionState:
    execution_id: str
    status: str = "pending"
    goal: str = ""
    attempt: int = 0
    plan: Any = None
    result: Any = None
    error: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionStore:
    """Small atomic JSON store; validates lifecycle transitions."""

    TRANSITIONS = {
        "pending": {"running"},
        "running": {"retrying", "completed", "failed"},
        "retrying": {"running", "failed"},
        "completed": set(),
        "failed": {"retrying"},
    }

    def __init__(self, path: str = "data/executions.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})

    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def save(self, state: ExecutionState) -> ExecutionState:
        data = self._read()
        previous = data.get(state.execution_id)
        if previous:
            old_status = previous.get("status", "pending")
            if state.status != old_status and state.status not in self.TRANSITIONS.get(old_status, set()):
                raise InvalidExecutionTransition(f"invalid execution transition: {old_status} -> {state.status}")
        state.updated_at = datetime.now(timezone.utc).isoformat()
        data[state.execution_id] = asdict(state)
        self._write(data)
        return state

    def transition(self, execution_id: str, status: str, **updates) -> ExecutionState:
        state = self.get(execution_id)
        if not state:
            if status != "pending":
                raise KeyError(execution_id)
            state = ExecutionState(execution_id=execution_id)
        state.status = status
        for key, value in updates.items():
            setattr(state, key, value)
        return self.save(state)

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        raw = self._read().get(execution_id)
        return ExecutionState(**raw) if raw else None

    def resumable(self):
        return [ExecutionState(**raw) for raw in self._read().values() if raw.get("status") in {"running", "retrying"}]
