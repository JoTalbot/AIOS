class MultiAgentNegotiation:
    def __init__(self):
        self.proposals = []

    def propose(self, agent, decision):
        self.proposals.append({"agent": agent, "decision": decision})

    def consensus(self):
        return self.proposals[0] if self.proposals else None
