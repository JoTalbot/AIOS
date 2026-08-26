class EvolutionLoop:
    def __init__(self, evaluator, optimizer):
        self.evaluator = evaluator
        self.optimizer = optimizer

    def run_cycle(self, metrics):
        score = self.evaluator.evaluate(metrics)
        return self.optimizer.optimize(score)
