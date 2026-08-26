"""Agent lifecycle state machine."""

from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    ACTING = "acting"
    LEARNING = "learning"
    STOPPED = "stopped"


class AgentStateMachine:
    def __init__(self):
        self.state = AgentState.IDLE

    def transition(self, state):
        self.state = state

    def current(self):
        return self.state
