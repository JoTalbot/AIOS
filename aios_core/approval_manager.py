"""AIOS Approval Manager Layer v2.1.1

Manages human approvals for critical actions.
"""

from .policy_loader import PolicyLoader


class ApprovalManager:
    """Manages approval workflows for critical actions."""

    def __init__(self, policy_loader=None):
        self.approvals = []
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()

    def request(self, action: dict):
        """Request approval for an action.

        Actions whose scope is listed in the governance policy as requiring
        human oversight are held as ``pending``; safe low-risk actions are
        auto-approved.
        """
        scope = action.get("scope")
        risk = action.get("risk", "low")
        # Constitutional / federated scopes always require human oversight,
        # independent of policy availability. Policy may add more scopes.
        constitutional_scopes = {"global", "constitution", "federation"}
        policy_scopes = set(self.policies.approval_required_scopes)
        required_scopes = constitutional_scopes | policy_scopes
        needs_human = (scope in required_scopes) or risk in ("high", "critical")
        status = "pending" if needs_human else "auto_approved"
        approval = {"action": action, "status": status}
        self.approvals.append(approval)
        return approval

    def approve(self, approval_id: int):
        """Approve a pending action."""
        if approval_id < len(self.approvals):
            self.approvals[approval_id]["status"] = "approved"
            return self.approvals[approval_id]
        return None

    def deny(self, approval_id: int):
        """Deny a pending action."""
        if approval_id < len(self.approvals):
            self.approvals[approval_id]["status"] = "denied"
            return self.approvals[approval_id]
        return None

    def history(self):
        """Return approval history."""
        return self.approvals

    def approve(self, approval_id: int):
        """Approve an action."""
        if approval_id < len(self.approvals):
            self.approvals[approval_id]["status"] = "approved"
            return self.approvals[approval_id]
        return None

    def deny(self, approval_id: int):
        """Deny an action."""
        if approval_id < len(self.approvals):
            self.approvals[approval_id]["status"] = "denied"
            return self.approvals[approval_id]
        return None

    def history(self):
        """Return approval history."""
        return self.approvals
