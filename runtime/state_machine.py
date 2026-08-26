"""Runtime lifecycle state machine for AIOS execution flows."""

from enum import Enum


class LifecycleState(str, Enum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


_TRANSITIONS = {
    LifecycleState.CREATED: {LifecycleState.PLANNED},
    LifecycleState.PLANNED: {LifecycleState.RUNNING},
    LifecycleState.RUNNING: {
        LifecycleState.COMPLETED,
        LifecycleState.RECOVERING,
        LifecycleState.FAILED,
    },
    LifecycleState.RECOVERING: {
        LifecycleState.RUNNING,
        LifecycleState.FAILED,
    },
    LifecycleState.COMPLETED: set(),
    LifecycleState.FAILED: set(),
}


class LifecycleStateMachine:
    """Controls valid execution lifecycle transitions."""

    def __init__(self):
        self.state = LifecycleState.CREATED

    def transition(self, target: LifecycleState):
        allowed = _TRANSITIONS[self.state]

        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state} -> {target}"
            )

        self.state = target
        return self.state

    def can_transition(self, target: LifecycleState) -> bool:
        return target in _TRANSITIONS[self.state]
