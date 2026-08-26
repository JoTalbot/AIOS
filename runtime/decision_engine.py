class DecisionEngine:
    def __init__(self):
        self.decisions = []

    def decide(self, options):
        decision = options[0] if options else None
        self.decisions.append(decision)
        return decision
