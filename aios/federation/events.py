FEDERATION_EVENTS = {
    "joined": "federation.joined",
    "discovered": "node.discovered",
    "task": "task.federated",
    "consensus": "consensus.reached",
    "sync": "knowledge.synced",
    "recovered": "node.recovered",
}

class FederationEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event, payload=None):
        self.events.append((event, payload))
