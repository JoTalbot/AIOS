"""Persistent execution state for restart-safe AIOS vNext runs."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ExecutionState:
    execution_id: str
    status: str = "running"
    goal: str = ""
    attempt: int = 0
    plan: Any = None
    result: Any = None
    error: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionStore:
    """Small atomic JSON store; designed as a replaceable persistence adapter."""

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
        state.updated_at = datetime.now(timezone.utc).isoformat()
        data = self._read()
        data[state.execution_id] = asdict(state)
        self._write(data)
        return state

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        raw = self._read().get(execution_id)
        return ExecutionState(**raw) if raw else None

    def resumable(self):
        return [ExecutionState(**raw) for raw in self._read().values() if raw.get("status") == "running"]
