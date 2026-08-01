"""
Module for scanning secrets in CI pipeline using GitGuardian or SecretScanner.

Author: MetaCognitiveCoder
"""

import os
import sys
from typing import List
from dataclasses import dataclass
from gitguardian import GitGuardian
from secretscanner import SecretScanner

@dataclass
class Secret:
    """Class for storing secret information."""
    name: str
    value: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan secrets in the target path using GitGuardian or SecretScanner.

    Args:
        target_path (str): Path to scan for secrets.

    Returns:
        List[Secret]: List of secrets found.
    """
    try:
        gg = GitGuardian(api_key=os.environ.get('GITGUARDIAN_API_KEY'))
        scanner = SecretScanner()
        secrets = scanner.scan(target_path)
        return [Secret(secret.name, secret.value) for secret in secrets]
    except Exception as e:
        print(f"Error scanning secrets: {e}")
        return []

def check_secrets_in_files(project_path: str) -> bool:
    """
    Check if there are any secrets in the project files.

    Args:
        project_path (str): Path to the project.

    Returns:
        bool: True if secrets are found, False otherwise.
    """
    try:
        secrets = scan_secrets(project_path)
        return len(secrets) > 0
    except Exception as e:
        print(f"Error checking secrets in files: {e}")
        return False

def main():
    """
    Main function for testing.
    """
    project_path = os.path.dirname(os.path.abspath(__file__))
    if check_secrets_in_files(project_path):
        print("Secrets found in project files.")
    else:
        print("No secrets found in project files.")

if __name__ == '__main__':
    main()

__all__ = ['scan_secrets', 'check_secrets_in_files']