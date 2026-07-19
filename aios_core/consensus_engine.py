"""AIOS Consensus Engine

Coordinates distributed agreement over proposals using weighted voting.
"""


class ConsensusEngine:
    """Reaches consensus across participants on submitted proposals."""

    def __init__(self, threshold: float = 0.5):
        self.proposals = {}
        self.threshold = threshold
        self._next_id = 0

    def submit(self, proposal, participants: int = 1) -> int:
        """Submit a proposal and return its id."""
        pid = self._next_id
        self._next_id += 1
        self.proposals[pid] = {
            "proposal": proposal,
            "votes": {"approve": 0, "reject": 0},
            "participants": max(1, participants),
            "status": "open",
        }
        return pid

    def vote(self, proposal_id: int, vote: str) -> dict:
        """Cast a vote (``approve``/``reject``) on a proposal."""
        p = self.proposals.get(proposal_id)
        if p is None or p["status"] != "open":
            return None
        if vote in p["votes"]:
            p["votes"][vote] += 1
        return p

    def reach_consensus(self, proposal_id: int) -> dict:
        """Evaluate a proposal against the threshold and close it."""
        p = self.proposals.get(proposal_id)
        if p is None:
            return None
        total = p["votes"]["approve"] + p["votes"]["reject"]
        ratio = (p["votes"]["approve"] / total) if total else 0.0
        agreed = ratio >= self.threshold
        p["status"] = "consensus" if agreed else "rejected"
        p["agreement_ratio"] = round(ratio, 3)
        return p

    def open_proposals(self) -> list:
        """Ids of proposals still open."""
        return [pid for pid, p in self.proposals.items() if p["status"] == "open"]
