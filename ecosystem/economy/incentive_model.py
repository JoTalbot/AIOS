class IncentiveModel:
    """Agent incentive design foundation."""

    def calculate(self, performance):
        return {
            "performance": performance,
            "incentive": 0
        }
