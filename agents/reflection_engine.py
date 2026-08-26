class ReflectionEngine:
    def __init__(self):
        self.history = []

    def reflect(self, action, result):
        review = {
            "action": action,
            "result": result,
            "improved": bool(result)
        }
        self.history.append(review)
        return review

    def latest(self):
        return self.history[-1] if self.history else None
