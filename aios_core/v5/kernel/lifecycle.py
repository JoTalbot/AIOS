from enum import Enum


class SystemState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    FAILED = "failed"


class LifecycleManager:
    def __init__(self):
        self.state = SystemState.STARTING

    def start(self):
        self.state = SystemState.RUNNING

    def stop(self):
        self.state = SystemState.STOPPING
