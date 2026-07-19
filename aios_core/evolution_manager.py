"""AIOS Evolution Manager v2.1.1

Controls the safe lifecycle of AIOS modifications, gated by policy.
"""

from .policy_loader import PolicyLoader


class EvolutionManager:
    """Manages controlled evolution of the AIOS system."""

    def __init__(self, version: str = "2.1.1", policy_loader=None):
        self.version = version
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()
        self.stages = [
            "proposal",
            "sandbox",
            "simulation",
            "audit",
            "approval",
            "deployment",
        ]
        self.proposals = []
        self.evolution_policy = self.policies.get("evolution_policy", {}) or {}

    def create_proposal(self, change: dict) -> dict:
        """Create a change proposal at the first pipeline stage."""
        proposal = {
            "status": "PROPOSAL_CREATED",
            "change": change,
            "pipeline": self.stages,
            "stage_index": 0,
        }
        self.proposals.append(proposal)
        return proposal

    def can_deploy(self, audit_passed: bool, approved: bool) -> bool:
        """Check if a change may deploy given audit and approval results.

        Honours the evolution policy restriction that constitution changes
        require explicit approval.
        """
        if not (audit_passed and approved):
            return False
        restrictions = self.evolution_policy.get("evolution_policy", {}).get(
            "restrictions", {}
        ) if isinstance(self.evolution_policy, dict) else {}
        if isinstance(restrictions, dict) and restrictions.get(
            "constitution_changes"
        ) == "approval_required":
            return approved
        return True

    def advance_stage(self, proposal_id: int) -> dict:
        """Advance a proposal to the next stage."""
        if proposal_id < len(self.proposals):
            proposal = self.proposals[proposal_id]
            if proposal["stage_index"] < len(self.stages) - 1:
                proposal["stage_index"] += 1
                proposal["status"] = self.stages[proposal["stage_index"]].upper()
            return proposal
        return None
