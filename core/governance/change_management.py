from dataclasses import dataclass


@dataclass
class ChangeProposal:
    name: str
    risk: float
    payload: dict


class ChangeProposalEngine:

    def __init__(self):
        self.proposals = []

    def create(self, proposal):
        self.proposals.append(proposal)
        return proposal
