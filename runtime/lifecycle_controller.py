"""AIOS lifecycle controller foundation.

Coordinates startup, running state, and shutdown hooks.
"""

from dataclasses import dataclass


@dataclass
class LifecycleState:
    status: str = "initialized"


class LifecycleController:
    def __init__(self):
        self.state = LifecycleState()

    def start(self):
        self.state.status = "running"
        return self.state

    def stop(self):
        self.state.status = "stopped"
        return self.state
