"""Data Encryption for AIOS"""

from cryptography.fernet import Fernet
from typing import Optional


class EncryptionManager:
    """Symmetric encryption using Fernet (AES)."""

    def __init__(self, key: Optional[bytes] = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())

    def decrypt(self, token: bytes) -> str:
        return self.cipher.decrypt(token).decode()

    def get_key(self) -> bytes:
        return self.key


encryption = EncryptionManager()
