"""
Module for scanning secrets in a project using secrets-scanner library.

Author: MetaCognitiveCoder
"""

import os
import secrets_scanner
from dataclasses import dataclass
from typing import List

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Dataclass for storing secret information."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the project for secrets using secrets-scanner library.

    Args:
    target_path (str): Path to the project root.

    Returns:
    List[Secret]: List of secrets found in the project.
    """
    try:
        scanner = secrets_scanner.Scanner()
        scanner.scan(target_path)
        secrets_found = []
        for file in scanner.files:
            for secret in file.secrets:
                secrets_found.append(Secret(file.path, secret))
        return secrets_found
    except Exception as e:
        print(f"Error scanning secrets: {e}")
        return []

def main():
    target_path = "tools/aios_dobavit_funktsiyu_skanirovaniya_165238.py"
    secrets = scan_secrets(target_path)
    if secrets:
        print("Secrets found:")
        for secret in secrets:
            print(f"Path: {secret.path}, Secret: {secret.secret}")
    else:
        print("No secrets found.")

if __name__ == '__main__':
    main()