"""Restore registered components from persisted kernel events."""


class RegistryRecovery:
    def __init__(self, event_store):
        self.event_store = event_store

    def restore(self, registry):
        for event in self.event_store.replay():
            if event.name == "component.registered":
                payload = event.payload
                registry.register(
                    payload.get("name"),
                    payload.get("component"),
                )

        return registry
