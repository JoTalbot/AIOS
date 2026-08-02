"""
CSRF Protection for AIOS
"""
import secrets
import hashlib
from typing import Dict
from datetime import datetime, timezone, timedelta

class CSRFProtection:
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.tokens: Dict[str, datetime] = {}
    
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        token = secrets.token_hex(32)
        # Store with expiry
        self.tokens[token] = datetime.now(timezone.utc) + timedelta(hours=1)
        # Cleanup old tokens
        self._cleanup()
        return token
    
    def validate_token(self, token: str) -> bool:
        """Validate CSRF token"""
        if token not in self.tokens:
            return False
        expiry = self.tokens[token]
        if datetime.now(timezone.utc) > expiry:
            del self.tokens[token]
            return False
        # Token is valid, remove after use (one-time) or keep for session
        # For now keep but could delete for one-time use
        return True
    
    def _cleanup(self):
        """Remove expired tokens"""
        now = datetime.now(timezone.utc)
        expired = [t for t, exp in self.tokens.items() if now > exp]
        for t in expired:
            del self.tokens[t]

# Global CSRF instance
csrf_protection = CSRFProtection()

def get_csrf_token(session_id: str = "default") -> str:
    return csrf_protection.generate_token(session_id)

def validate_csrf_token(token: str) -> bool:
    return csrf_protection.validate_token(token)
