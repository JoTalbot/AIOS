class OptimizerBridge:
    def __init__(self, metrics=None, optimizer=None):
        self.metrics = metrics
        self.optimizer = optimizer

    def evaluate(self, strategy):
        score = self.metrics.latest() if self.metrics else 0
        if self.optimizer:
            return self.optimizer.update(strategy, score)
        return score
