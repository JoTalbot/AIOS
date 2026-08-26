"""Kernel lifecycle hooks with runtime recovery integration."""

from enum import Enum


class LifecyclePhase(str, Enum):
    INIT = "init"
    REGISTER = "register"
    START = "start"
    RUN = "run"
    STOP = "stop"


class LifecycleManager:
    def __init__(self, agent_manager=None):
        self.phase = LifecyclePhase.INIT
        self.listeners = []
        self.agent_manager = agent_manager

    def subscribe(self, listener):
        self.listeners.append(listener)

    def transition(self, phase: LifecyclePhase):
        previous = self.phase
        self.phase = phase

        for listener in self.listeners:
            listener(previous, phase)

        return self.phase

    def startup(self):
        self.transition(LifecyclePhase.START)
        if self.agent_manager:
            self.agent_manager.recover()
        self.transition(LifecyclePhase.RUN)
        return self.phase

    def shutdown(self):
        if self.agent_manager:
            self.agent_manager.snapshot()
        self.transition(LifecyclePhase.STOP)
        return self.phase
