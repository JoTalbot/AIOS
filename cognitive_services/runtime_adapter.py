"""AIOS Runtime Adapter boundary for cognitive services."""


class CognitiveRuntimeAdapter:
    def __init__(self, registry):
        self.registry = registry

    def health(self):
        return self.registry.health()

    def execute(self, service_name, payload):
        service = self.registry.get(service_name)
        if service is None:
            raise ValueError(f"Unknown cognitive service: {service_name}")
        return service.process(payload)
