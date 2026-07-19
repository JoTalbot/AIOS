"""AIOS Approval Manager Layer v2.1.1

Manages human approvals for critical actions.
"""


class ApprovalManager:
    """Manages approval workflows for critical actions."""

    def __init__(self):
        self.approvals = []

    def request(self, action: dict):
        """Request approval for an action."""
        approval = {"action": action, "status": "pending"}
        self.approvals.append(approval)
        return approval

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
