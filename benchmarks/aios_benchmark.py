class AIOSBenchmark:
    def __init__(self):
        self.results = []

    def record(self, name, score, metadata=None):
        self.results.append({
            "name": name,
            "score": score,
            "metadata": metadata or {}
        })
        return self.results[-1]

    def summary(self):
        return self.results
