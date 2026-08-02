class SocialGraph:
    """Agent social relationship graph foundation."""

    def __init__(self):
        self.links = {}

    def connect(self, source, target):
        self.links.setdefault(source, []).append(target)

    def neighbors(self, agent):
        return self.links.get(agent, [])
