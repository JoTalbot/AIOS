from .lifecycle import LifecycleManager, LifecyclePhase
from .registry import KernelRegistry
from .state import KernelState, RuntimeStatus


class Kernel:
    def __init__(self):
        self.state = KernelState()
        self.registry = KernelRegistry()
        self.lifecycle = LifecycleManager()

    def start(self):
        self.lifecycle.transition(LifecyclePhase.START)
        self.state.status = RuntimeStatus.RUNNING

    def stop(self):
        self.lifecycle.transition(LifecyclePhase.STOP)
        self.state.status = RuntimeStatus.STOPPED

    def register(self, name, component):
        self.registry.register(name, component)
