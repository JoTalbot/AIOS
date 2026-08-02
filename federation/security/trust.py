class TrustManager:
    """Federation trust evaluation foundation."""

    def __init__(self):
        self.trust_scores = {}

    def set_trust(self, node_id, score):
        self.trust_scores[node_id] = score

    def get_trust(self, node_id):
        return self.trust_scores.get(node_id, 0)
