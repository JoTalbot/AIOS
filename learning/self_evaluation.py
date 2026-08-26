class SelfEvaluation:
    def __init__(self, metrics):
        self.metrics = metrics

    def evaluate(self):
        score = self.metrics.calculate()
        return {"score": score, "status": "improving" if score < 1 else "stable"}
