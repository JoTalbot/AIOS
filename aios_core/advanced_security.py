"""Advanced Security Module for AIOS"""

import hashlib
import secrets
from typing import Dict, List


class AdvancedSecurity:
    """Multi-layer security system.

    Provides threat detection, sensitive-data hashing, and API key generation.
    """

    def __init__(self):
        self.threats: List[Dict] = []
        self.policies: Dict = {}

    def detect_threat(self, request: Dict) -> bool:
        """Return ``True`` and log if *request* matches a threat signature."""
        # Simple threat detection
        if request.get("ip") in ["0.0.0.0", "127.0.0.1"]:
            self.threats.append({"type": "suspicious_ip", "request": request})
            return True
        return False

    def encrypt_sensitive(self, data: str) -> str:
        """Return SHA-256 hex digest of *data*."""
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_api_key(self) -> str:
        """Generate a cryptographically random URL-safe token."""
        return secrets.token_urlsafe(32)

    def stats(self) -> dict:
        """Return count of detected threats."""
        return {"threats_detected": len(self.threats)}
