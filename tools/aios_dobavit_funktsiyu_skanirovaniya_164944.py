"""
Module for scanning secrets in a project.

This module uses the secrets-scanner library to scan for secrets in the project.
"""

import os
from dataclasses import dataclass
from typing import List
from secrets_scanner import SecretsScanner

__all__ = ['scan_secrets']

@dataclass
class Secret:
    """Class to represent a secret."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan for secrets in the project.

    Args:
    target_path (str): The path to scan for secrets.

    Returns:
    List[Secret]: A list of secrets found in the project.
    """
    try:
        scanner = SecretsScanner()
        secrets = scanner.scan(target_path)
        return [Secret(path, secret) for path, secret in secrets]
    except Exception as e:
        print(f"Error scanning secrets: {e}")
        return []

def main():
    """
    Test the scan_secrets function.
    """
    target_path = 'tools'
    secrets = scan_secrets(target_path)
    for secret in secrets:
        print(f"Secret found at {secret.path}: {secret.secret}")

if __name__ == '__main__':
    main()