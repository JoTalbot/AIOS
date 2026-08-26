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
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def transition(self, phase: LifecyclePhase):
        previous = self.phase
        self.phase = phase

        for listener in self.listeners:
            listener(previous, phase)

        return self.phase
