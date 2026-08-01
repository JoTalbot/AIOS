import os
import secrets_scanner
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['find_secrets']

@dataclass
class Secret:
    """Dataclass to represent a secret found in the project."""
    path: str
    secret: str

def find_secrets(target_path: str) -> List[Secret]:
    """
    Scans the project for secrets using the secrets-scanner library.

    Args:
    target_path (str): The path to the project to scan.

    Returns:
    List[Secret]: A list of secrets found in the project.
    """
    try:
        scanner = secrets_scanner.Scanner()
        scanner.scan(target_path)
        secrets = scanner.get_secrets()
        return [Secret(path, secret) for path, secret in secrets.items()]
    except Exception as e:
        print(f"Error scanning for secrets: {e}")
        return []

def test_find_secrets():
    """Tests the find_secrets function."""
    target_path = 'tests'
    secrets = find_secrets(target_path)
    assert len(secrets) > 0, "No secrets found"

def test_find_secrets_empty_dir():
    """Tests the find_secrets function with an empty directory."""
    target_path = 'tests/empty_dir'
    secrets = find_secrets(target_path)
    assert len(secrets) == 0, "Secrets found in empty directory"

if __name__ == '__main__':
    target_path = 'tools'
    secrets = find_secrets(target_path)
    for secret in secrets:
        print(f"Secret found at {secret.path}: {secret.secret}")
    test_find_secrets()
    test_find_secrets_empty_dir()