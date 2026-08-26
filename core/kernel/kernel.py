from .lifecycle import LifecycleManager, LifecyclePhase
from .registry import KernelRegistry
from .state import KernelState, RuntimeStatus
from core.events.bus import EventBus


class Kernel:
    def __init__(self):
        self.state = KernelState()
        self.registry = KernelRegistry()
        self.lifecycle = LifecycleManager()
        self.events = EventBus()

    def start(self):
        self.lifecycle.transition(LifecyclePhase.START)
        self.state.status = RuntimeStatus.RUNNING
        self.events.publish(
            "kernel.started",
            {"status": self.state.status}
        )

    def stop(self):
        self.lifecycle.transition(LifecyclePhase.STOP)
        self.state.status = RuntimeStatus.STOPPED
        self.events.publish(
            "kernel.stopped",
            {"status": self.state.status}
        )

    def register(self, name, component):
        self.registry.register(name, component)
        self.events.publish(
            "component.registered",
            {"name": name, "component": component}
        )
