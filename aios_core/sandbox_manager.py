"""
AIOS Sandbox Manager v2.1.1

Provides isolated environment management for testing changes.
"""


class SandboxManager:
    def __init__(self):
        self.sandboxes = []

    def create(self, proposal_id: str) -> dict:
        sandbox = {
            "proposal_id": proposal_id,
            "status": "CREATED",
            "isolated": True,
        }
        self.sandboxes.append(sandbox)
        return sandbox

    def destroy(self, proposal_id: str) -> bool:
        self.sandboxes = [s for s in self.sandboxes if s["proposal_id"] != proposal_id]
        return True
