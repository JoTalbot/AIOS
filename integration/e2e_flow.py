"""End-to-end AIOS execution flow foundation."""

class E2EFlow:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    def run(self, request):
        return self.coordinator.execute(request) if self.coordinator else None
