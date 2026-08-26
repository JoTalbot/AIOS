class RegressionDetector:

    def compare(self, previous, current):
        return {
            "regression": current < previous,
            "previous": previous,
            "current": current
        }
