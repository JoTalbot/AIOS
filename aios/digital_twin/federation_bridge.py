"""Bridge between Digital Twin and Federation layers."""

class FederationTwinBridge:
    def __init__(self, twin, federation):
        self.twin = twin
        self.federation = federation

    def sync_state(self):
        return {
            "twin": self.twin.twin_id,
            "federation": self.federation.federation_id,
        }

    def broadcast_prediction(self, prediction):
        return {"prediction": prediction, "broadcast": True}
