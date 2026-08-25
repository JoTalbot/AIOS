"""Validated lifecycle transitions for runtime agents."""

from enum import Enum


class AgentState(Enum):
    """States supported by the v20 runtime foundation."""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class LifecycleManager:
    """Fail closed on unknown agents and invalid state transitions."""

    def __init__(self) -> None:
        self.states: dict[str, AgentState] = {}

    def register(self, agent_id: str) -> AgentState:
        if agent_id in self.states:
            raise ValueError(f"agent already registered: {agent_id}")
        return self._set(agent_id, AgentState.CREATED)

    def ready(self, agent_id: str) -> AgentState:
        self._require(agent_id, AgentState.CREATED)
        return self._set(agent_id, AgentState.READY)

    def start(self, agent_id: str) -> AgentState:
        self._require(agent_id, AgentState.READY)
        return self._set(agent_id, AgentState.RUNNING)

    def stop(self, agent_id: str) -> AgentState:
        self._require(agent_id, AgentState.RUNNING)
        return self._set(agent_id, AgentState.STOPPED)

    def fail(self, agent_id: str) -> AgentState:
        current = self._get(agent_id)
        if current in {AgentState.STOPPED, AgentState.FAILED}:
            raise RuntimeError(f"cannot fail agent from {current.value}")
        return self._set(agent_id, AgentState.FAILED)

    def _get(self, agent_id: str) -> AgentState:
        try:
            return self.states[agent_id]
        except KeyError as exc:
            raise KeyError(f"unknown agent: {agent_id}") from exc

    def _require(self, agent_id: str, expected: AgentState) -> None:
        current = self._get(agent_id)
        if current is not expected:
            raise RuntimeError(f"expected {expected.value}, got {current.value}")

    def _set(self, agent_id: str, state: AgentState) -> AgentState:
        self.states[agent_id] = state
        return state
