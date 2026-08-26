class IntelligenceConsensus:

    def vote(self, proposals):
        if not proposals:
            return None

        scores = {}

        for proposal in proposals:
            action = proposal["action"]
            scores[action] = scores.get(action, 0) + proposal.get("confidence", 0)

        return max(scores, key=scores.get)
