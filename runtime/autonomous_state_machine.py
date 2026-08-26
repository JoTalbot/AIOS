"""State machine for AIOS autonomous runtime."""

from enum import Enum


class AIOSState(Enum):
    OBSERVE = "observe"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    LEARN = "learn"
    EVOLVE = "evolve"


class AutonomousStateMachine:
    def __init__(self):
        self.state = AIOSState.OBSERVE

    def transition(self, next_state):
        self.state = next_state
        return self.state

    def current(self):
        return self.state.value
