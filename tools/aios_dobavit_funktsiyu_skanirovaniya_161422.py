# tools/aios_dobavit_funktsiyu_skanirovaniya_161422.py

import os
import secrets
from dataclasses import dataclass
from typing import List, Optional

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class representing a secret."""
    path: str
    value: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the project for secrets.

    Args:
    target_path: The path to start scanning from.

    Returns:
    A list of secrets found in the project.
    """
    secrets_found = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if secrets.compare_digest(content, 'secret_key'):
                        secrets_found.append(Secret(file_path, 'secret_key'))
                    elif secrets.compare_digest(content, 'secret_token'):
                        secrets_found.append(Secret(file_path, 'secret_token'))
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_found

def test_scan_secrets():
    """Test the scan_secrets function."""
    target_path = 'tests/fixtures'
    secrets_found = scan_secrets(target_path)
    assert len(secrets_found) == 2
    assert secrets_found[0].path == 'tests/fixtures/file1.txt'
    assert secrets_found[0].value == 'secret_key'
    assert secrets_found[1].path == 'tests/fixtures/file2.txt'
    assert secrets_found[1].value == 'secret_token'

def test_scan_secrets_empty_directory():
    """Test the scan_secrets function with an empty directory."""
    target_path = 'tests/fixtures/empty'
    secrets_found = scan_secrets(target_path)
    assert len(secrets_found) == 0

if __name__ == '__main__':
    test_scan_secrets()
    print("All tests passed.")