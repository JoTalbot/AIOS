class CompetitorTracker:
    """OLX competitor monitoring foundation."""

    def __init__(self):
        self.history = []

    def track(self, competitor):
        self.history.append(competitor)
        return competitor

    def changes(self):
        return self.history
