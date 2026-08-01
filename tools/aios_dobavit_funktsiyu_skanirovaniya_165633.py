# tools/aios_dobavit_funktsiyu_skanirovaniya_165633.py

import os
import secretsdetector
from dataclasses import dataclass
from typing import List
from pathlib import Path

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the project for secrets.

    Args:
    target_path (str): The path to the project root.

    Returns:
    List[Secret]: A list of secrets found in the project.
    """
    secrets = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    secret = secretsdetector.detect_secrets(content)
                    if secret:
                        secrets.append(Secret(path=file_path, secret=secret))
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets

def test_scan_secrets():
    """Test the scan_secrets function."""
    target_path = 'tests/fixtures/project'
    secrets = scan_secrets(target_path)
    assert len(secrets) > 0

def test_scan_secrets_empty_project():
    """Test the scan_secrets function with an empty project."""
    target_path = 'tests/fixtures/empty_project'
    secrets = scan_secrets(target_path)
    assert len(secrets) == 0

if __name__ == '__main__':
    import unittest
    unittest.main(argv=[os.path.basename(__file__)])