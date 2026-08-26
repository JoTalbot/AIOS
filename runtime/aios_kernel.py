"""Central kernel coordinating AIOS subsystems."""


class AIOSKernel:
    def __init__(self):
        self.components = {}
        self.state = "idle"

    def register(self, name, component):
        self.components[name] = component

    def transition(self, state: str):
        self.state = state

    def status(self):
        return {
            "state": self.state,
            "components": list(self.components.keys()),
        }
