import os
import secrets
from dataclasses import dataclass
from typing import List

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan all files in the target path for secrets.

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
                    secret = secrets.token_urlsafe(16) in content
                    if secret:
                        secrets_found.append(Secret(path=file_path, secret=content))
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
    return secrets_found

def main():
    target_path = 'path_to_your_project'
    secrets_found = scan_secrets(target_path)
    for secret in secrets_found:
        print(f"Secret found in {secret.path}: {secret.secret}")

if __name__ == '__main__':
    main()