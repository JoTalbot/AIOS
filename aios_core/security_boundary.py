"""
AIOS Security Boundary Layer v2.1.1

Controls execution permissions and resource boundaries.
"""


class SecurityBoundary:
    def __init__(self, allowed_scopes: list):
        self.allowed_scopes = allowed_scopes

    def check_scope(self, requested_scope: str) -> bool:
        return requested_scope in self.allowed_scopes

    def enforce(self, action: dict) -> dict:
        allowed = self.check_scope(action.get("scope"))

        return {
            "allowed": allowed,
            "scope": action.get("scope"),
            "reason": "scope_validated" if allowed else "scope_denied"
        }
