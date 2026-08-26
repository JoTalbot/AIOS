"""AIOS runtime health checks."""

class HealthStatus:
    def __init__(self, healthy=True, components=None):
        self.healthy = healthy
        self.components = components or {}


def check_health(runtime=None):
    return HealthStatus(healthy=runtime is not None)
