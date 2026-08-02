class SimulationEnvironment:
    """AIOS simulation environment foundation."""

    def __init__(self):
        self.state = {}

    def set_state(self, key, value):
        self.state[key] = value

    def get_state(self, key):
        return self.state.get(key)
