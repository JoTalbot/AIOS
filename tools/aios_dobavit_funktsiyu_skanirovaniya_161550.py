import os
import secrets
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan all files in the target path and its subdirectories for secrets.

    Args:
    target_path (str): The path to scan for secrets.

    Returns:
    List[Secret]: A list of secrets found in the target path.
    """
    secrets_found = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if secrets.compare_digest(content, 'secret') or secrets.compare_digest(content, 'SECRET'):
                        secrets_found.append(Secret(path=file_path, secret=content))
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_found

if __name__ == '__main__':
    target_path = 'path_to_your_project'
    secrets_found = scan_secrets(target_path)
    for secret in secrets_found:
        print(f"Secret found at {secret.path}: {secret.secret}")