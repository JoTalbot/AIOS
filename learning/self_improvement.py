class SelfImprovement:
    def __init__(self, optimizer=None):
        self.optimizer = optimizer

    def improve(self, strategy, score):
        if self.optimizer:
            self.optimizer.update(strategy, score)
        return self.optimizer.best() if self.optimizer else strategy
