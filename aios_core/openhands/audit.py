"""OpenHands audit with secret masking and cryptographically linked checkpoints."""
import re
from typing import Any
from uuid import uuid4

from aios_core.audit_logger import AuditLogger

from .audit_chain import AuditChain, ChainCheckpoint
from .models import AgentRole

EVENT_PREFIX = "openhands"
CHECKPOINT_ACTION = "audit_checkpoint"
CRITICAL_ACTIONS = frozenset({"gate_pass", "gate_block", "handoff", "security_review"})
_SENSITIVE_KEY = re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|cookie|credential|authorization)", re.IGNORECASE)
_SENSITIVE_VALUE = re.compile(r"\b[A-Za-z0-9+/=_-]{20,}\b")
MASK = "***"


def mask_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: MASK if _SENSITIVE_KEY.search(str(key)) else mask_secrets(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [mask_secrets(item) for item in obj]
    if isinstance(obj, str):
        return _SENSITIVE_VALUE.sub(MASK, obj)
    return obj


class OHAuditLogger:
    """OpenHands audit facade with durable, cryptographically linked checkpoints."""

    def __init__(self, logger: AuditLogger | None = None, chain: AuditChain | None = None) -> None:
        self._logger = logger or AuditLogger()
        if chain is not None:
            self._chain = chain
        else:
            persisted = [event for event in self._logger.query(limit=100000) if str(event.get("type", "")).startswith(f"{EVENT_PREFIX}.")]
            self._chain = AuditChain.from_persisted(persisted)

    def log(self, action: str, task_id: str, agent: AgentRole | str, **fields: Any) -> dict:
        role = agent.value if isinstance(agent, AgentRole) else str(agent)
        event_id = uuid4().hex
        event = mask_secrets({"type": f"{EVENT_PREFIX}.{action}", "task_id": task_id, "agent": role, **fields})
        chain_event = self._chain.append(event_id, event)
        event.update({"event_id": event_id, "parent_event_id": chain_event.parent_event_id, "event_hash": chain_event.event_hash})
        result = self._logger.record(event)
        if action in CRITICAL_ACTIONS:
            self.checkpoint(task_id, agent, gate_decision=fields.get("decision"), commit_sha=fields.get("commit_sha"), diff_hash=fields.get("diff_hash"))
        return result

    def log_transition(self, task_id: str, agent: AgentRole | str, src: str, dst: str, **fields: Any) -> dict:
        return self.log("transition", task_id, agent, src=src, dst=dst, **fields)

    def log_decision(self, task_id: str, agent: AgentRole | str, decision: str, **fields: Any) -> dict:
        return self.log("decision", task_id, agent, decision=decision, **fields)

    def checkpoint(self, task_id: str = "system", agent: AgentRole | str = "system", *, gate_decision: str | None = None, commit_sha: str | None = None, diff_hash: str | None = None) -> ChainCheckpoint:
        checkpoint = self._chain.checkpoint(task_id=task_id, agent=agent.value if isinstance(agent, AgentRole) else str(agent), gate_decision=gate_decision, commit_sha=commit_sha, diff_hash=diff_hash)
        role = agent.value if isinstance(agent, AgentRole) else str(agent)
        event = {
            "type": f"{EVENT_PREFIX}.{CHECKPOINT_ACTION}",
            "task_id": task_id,
            "agent": role,
            "sequence": checkpoint.sequence,
            "last_event_id": checkpoint.last_event_id,
            "root_hash": checkpoint.root_hash,
            "gate_decision": checkpoint.gate_decision,
            "commit_sha": checkpoint.commit_sha,
            "diff_hash": checkpoint.diff_hash,
            "previous_checkpoint_hash": checkpoint.previous_checkpoint_hash,
            "checkpoint_hash": checkpoint.checkpoint_hash,
        }
        self._logger.record(event)
        return checkpoint

    def verify_chain(self) -> bool:
        return self._chain.verify()

    @property
    def chain(self) -> AuditChain:
        return self._chain

    @property
    def backend(self) -> AuditLogger:
        return self._logger
