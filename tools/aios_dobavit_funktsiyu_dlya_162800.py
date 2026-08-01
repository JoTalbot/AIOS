# tools/aios_dobavit_funktsiyu_dlya_162800.py

import os
from dataclasses import dataclass
from typing import List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    path: str
    secret: str

def generate_key(password: str) -> bytes:
    """Generate a key from a password."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the target path for secrets.

    Args:
    target_path (str): The path to scan for secrets.

    Returns:
    List[Secret]: A list of secrets found.
    """
    secrets = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                    key = generate_key('mysecretpassword')
                    fernet = Fernet(key)
                    try:
                        fernet.decrypt(data)
                        secrets.append(Secret(file_path, fernet.decrypt(data).decode()))
                    except Exception as e:
                        # If decryption fails, it's not a secret
                        pass
            except Exception as e:
                # Handle any other exceptions
                print(f"Error scanning file {file_path}: {e}")
    return secrets

def test_scan_secrets():
    """Test the scan_secrets function."""
    target_path = 'tests/fixtures'
    secrets = scan_secrets(target_path)
    for secret in secrets:
        print(f"Secret found at {secret.path}: {secret.secret}")

if __name__ == '__main__':
    test_scan_secrets()