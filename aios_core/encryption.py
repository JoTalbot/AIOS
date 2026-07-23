"""Data Encryption for AIOS"""

from typing import Optional

from cryptography.fernet import Fernet


class EncryptionManager:
    """Symmetric encryption using Fernet (AES)."""

    def __init__(self, key: Optional[bytes] = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> bytes:
        """Execute encrypt."""
        return self.cipher.encrypt(data.encode())

    def decrypt(self, token: bytes) -> str:
        """Execute decrypt."""
        return self.cipher.decrypt(token).decode()

    def get_key(self) -> bytes:
        """Execute get key."""
        return self.key


encryption = EncryptionManager()
