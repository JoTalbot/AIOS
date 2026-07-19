"""AIOS Consensus Engine"""

class ConsensusEngine:
    def __init__(self):
        self.proposals = []

    def submit(self, proposal):
        self.proposals.append(proposal)
        return True

    def reach_consensus(self):
        return self.proposals
