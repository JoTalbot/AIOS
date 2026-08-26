class WorldModelLearning:
    def __init__(self, world_model):
        self.world_model = world_model
        self.history = []

    def learn(self, experience):
        self.history.append(experience)
        return self.world_model.update(experience)
