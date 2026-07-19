"""
AIOS Approval Workflow v2.1.1

Manages review and approval flow for constitutional decisions.
"""


class ApprovalWorkflow:
    def __init__(self):
        self.pending = []

    def submit(self, action: dict):
        request = {
            "status": "PENDING_REVIEW",
            "action": action
        }
        self.pending.append(request)
        return request

    def approve(self, index: int):
        self.pending[index]["status"] = "APPROVED"
        return self.pending[index]

    def reject(self, index: int):
        self.pending[index]["status"] = "REJECTED"
        return self.pending[index]
