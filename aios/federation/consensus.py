class ConsensusEngine:
    def evaluate(self, proposals):
        if not proposals:
            return None
        return max(proposals, key=lambda p: p.get("trust_weight", 0))
