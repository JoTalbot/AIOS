from .lifecycle import LifecycleManager, LifecyclePhase
from .registry import KernelRegistry
from .state import KernelState, RuntimeStatus
from .recovery import KernelRecovery
from core.events.bus import EventBus
from core.events.event import KernelEvent
from core.events.persistence import EventStore


class Kernel:
    def __init__(self):
        self.state = KernelState()
        self.registry = KernelRegistry()
        self.lifecycle = LifecycleManager()
        self.event_store = EventStore()
        self.events = EventBus(self.event_store)
        self.recovery = KernelRecovery(self.event_store)

        self.lifecycle.subscribe(
            self._on_lifecycle_change
        )

    def _on_lifecycle_change(self, previous, current):
        self.events.publish(
            KernelEvent(
                name="lifecycle.changed",
                source="kernel.lifecycle",
                payload={
                    "from": previous,
                    "to": current,
                },
            )
        )

    def restore(self):
        self.recovery.restore_status(self.state)

    def start(self):
        self.lifecycle.transition(LifecyclePhase.START)
        self.state.status = RuntimeStatus.RUNNING
        self.events.publish(
            KernelEvent(
                name="kernel.started",
                source="kernel",
                payload={"status": self.state.status},
            )
        )

    def stop(self):
        self.lifecycle.transition(LifecyclePhase.STOP)
        self.state.status = RuntimeStatus.STOPPED
        self.events.publish(
            KernelEvent(
                name="kernel.stopped",
                source="kernel",
                payload={"status": self.state.status},
            )
        )

    def register(self, name, component):
        self.registry.register(name, component)
        self.events.publish(
            KernelEvent(
                name="component.registered",
                source="kernel.registry",
                payload={
                    "name": name,
                    "component": component,
                },
            )
        )
