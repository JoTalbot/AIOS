class CollectiveLearning:
    """Collective learning foundation."""

    def __init__(self):
        self.experiences = []

    def learn(self, experience):
        self.experiences.append(experience)

    def knowledge(self):
        return self.experiences
