"""Federation bridge for swarm intelligence."""

class FederationSwarmBridge:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def distribute(self, task):
        return self.coordinator.route(task)
