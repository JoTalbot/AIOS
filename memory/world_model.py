class WorldModel:
    def __init__(self):
        self.state = {}
        self.history = []

    def update(self, observation):
        self.state.update(observation)
        self.history.append(dict(self.state))
        return self.state

    def predict(self, action):
        return {"action": action, "predicted_state": dict(self.state)}
