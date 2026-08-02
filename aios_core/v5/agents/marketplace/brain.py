class OLXIntelligenceBrain:
    """Unified intelligence layer for OLX Agent."""

    def __init__(self, analyzer=None, pricing=None, monitor=None, strategy=None, decision=None, feedback=None):
        self.analyzer = analyzer
        self.pricing = pricing
        self.monitor = monitor
        self.strategy = strategy
        self.decision = decision
        self.feedback = feedback

    def process(self, listings):
        analysis = self.analyzer.analyze(listings) if self.analyzer else {}
        prices = self.pricing.calculate(listings) if self.pricing else {}
        competitors = self.monitor.track(listings) if self.monitor else {}

        context = {
            "analysis": analysis,
            "prices": prices,
            "competitors": competitors,
        }

        plan = self.strategy.plan(context) if self.strategy else {}
        decision = self.decision.decide(plan) if self.decision else {}

        if self.feedback:
            self.feedback.record(decision)

        return decision
