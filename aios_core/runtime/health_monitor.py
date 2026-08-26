class HealthMonitor:
    def __init__(self):
        self.status = {}

    def update(self, component, state):
        self.status[component] = state

    def check(self):
        return self.status
