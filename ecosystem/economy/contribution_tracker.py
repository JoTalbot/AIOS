class ContributionTracker:
    """Agent contribution tracking foundation."""

    def __init__(self):
        self.contributions = {}

    def track(self, agent, value):
        self.contributions[agent] = value

    def get(self, agent):
        return self.contributions.get(agent, 0)
