class WorldModel:
    """Civilization world model foundation."""

    def __init__(self):
        self.state = {}

    def update(self, entity, value):
        self.state[entity] = value

    def observe(self):
        return self.state
