import os
from dataclasses import dataclass
from typing import List, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import getpass

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    name: str
    value: str
    type: str

def generate_key(password: str) -> bytes:
    """Generate a key for encryption."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'secret_key_salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_secret(value: str, key: bytes) -> str:
    """Encrypt a secret value."""
    fernet = Fernet(key)
    encrypted_value = fernet.encrypt(value.encode())
    return encrypted_value.decode()

def decrypt_secret(encrypted_value: str, key: bytes) -> str:
    """Decrypt a secret value."""
    fernet = Fernet(key)
    decrypted_value = fernet.decrypt(encrypted_value.encode())
    return decrypted_value.decode()

def scan_secrets(target_path: str) -> List[Secret]:
    """Scan the target path for secrets."""
    secrets = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'API_KEY' in content or 'API_TOKEN' in content:
                        secret = Secret('API_KEY', content, 'API_KEY')
                        secrets.append(secret)
                    elif 'PASSWORD' in content or 'PASSWORD=' in content:
                        secret = Secret('PASSWORD', content, 'PASSWORD')
                        secrets.append(secret)
                    elif 'TOKEN' in content:
                        secret = Secret('TOKEN', content, 'TOKEN')
                        secrets.append(secret)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
    return secrets

def main():
    password = getpass.getpass("Enter password for encryption: ")
    key = generate_key(password)
    target_path = input("Enter target path: ")
    secrets = scan_secrets(target_path)
    for secret in secrets:
        encrypted_value = encrypt_secret(secret.value, key)
        print(f"Secret {secret.name} encrypted: {encrypted_value}")

if __name__ == '__main__':
    main()