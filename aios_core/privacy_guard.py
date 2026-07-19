"""AIOS Privacy Guard Layer v2.1.1

Protects memory access according to data classification rules.
"""


class PrivacyGuard:
    """Manages privacy protection and data access control."""

    def __init__(self):
        self.protected = ["PERSONAL"]
        self.access_log = []

    def can_share(self, classification: str) -> bool:
        """Check if data can be shared."""
        return classification not in self.protected

    def check_access(self, request: dict) -> dict:
        """Check if data access is allowed."""
        allowed = self.can_share(request.get("classification"))
        
        result = {
            "allowed": allowed,
            "classification": request.get("classification"),
            "reason": "approved" if allowed else "personal_data_protected"
        }
        
        self.access_log.append(result)
        return result
