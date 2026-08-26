class WorldModelSimulator:
    def __init__(self, world_model=None):
        self.world_model = world_model

    def simulate(self, action, state=None):
        return {
            "action": action,
            "state": state,
            "predicted": True,
        }
