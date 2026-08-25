from enum import Enum


class AgentState(Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class LifecycleManager:
    def __init__(self):
        self.states = {}

    def register(self, agent_id):
        self.states[agent_id] = AgentState.CREATED

    def start(self, agent_id):
        self.states[agent_id] = AgentState.RUNNING

    def stop(self, agent_id):
        self.states[agent_id] = AgentState.STOPPED

    def fail(self, agent_id):
        self.states[agent_id] = AgentState.FAILED
