from enum import Enum


class LifecyclePhase(str, Enum):
    INIT = "init"
    REGISTER = "register"
    START = "start"
    RUN = "run"
    STOP = "stop"


class LifecycleManager:
    def __init__(self):
        self.phase = LifecyclePhase.INIT

    def transition(self, phase: LifecyclePhase):
        self.phase = phase
        return self.phase
