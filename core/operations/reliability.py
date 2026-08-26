class ReliabilityScorer:
    def score(self, metrics):
        failures = metrics.get("failures", 0)
        total = metrics.get("total", 1)
        return max(0, 1 - failures / total)
