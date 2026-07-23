"""JWT-based Authentication for AIOS"""

import time
from typing import Any, Dict, Optional

import jwt


class JWTManager:
    """Simple JWT token manager."""

    def __init__(self, secret: str = "aios-secret-key", algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_token(self, subject: str, roles: list = None, expires_in: int = 3600) -> str:
        """Execute create token."""
        payload = {
            "sub": subject,
            "roles": roles or ["user"],
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Execute verify token."""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.PyJWTError:
            return None

    def get_principal(self, token: str) -> Optional[Dict]:
        """Execute get principal."""
        payload = self.verify_token(token)
        if payload:
            return {
                "subject": payload.get("sub"),
                "roles": payload.get("roles", []),
                "token": token,
            }
        return None
