class AutonomousTrainer:
    def __init__(self, learner=None):
        self.learner = learner
        self.cycles = 0

    def train_cycle(self, experience):
        self.cycles += 1
        if self.learner:
            return self.learner.process(experience)
        return {"cycle": self.cycles, "status": "stored"}

    def stats(self):
        return {"cycles": self.cycles}
