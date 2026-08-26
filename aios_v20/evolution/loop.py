class EvolutionLoop:
    def __init__(self, evaluator, improver):
        self.evaluator = evaluator
        self.improver = improver

    def process(self, result):
        evaluation = self.evaluator.evaluate(result)
        return self.improver.propose(evaluation)
