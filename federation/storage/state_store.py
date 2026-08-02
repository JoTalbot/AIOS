class StateStore:
    """Federation persistent state storage foundation."""

    def __init__(self):
        self.state = {}

    def save(self, key, value):
        self.state[key] = value

    def load(self, key):
        return self.state.get(key)
