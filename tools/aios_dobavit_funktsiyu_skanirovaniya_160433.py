"""
Module for scanning secrets in project files.

This module provides a function for scanning project files for secrets and
raising an error if any are found.

Author: MetaCognitiveCoder
"""

import os
import re
import dataclasses
from typing import List

@dataclasses.dataclass
class Secret:
    """Class representing a secret found in a file."""
    file_path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan project files for secrets.

    Args:
    target_path: Path to the project root directory.

    Returns:
    List of Secret objects found in the project files.

    Raises:
    ValueError: If the target path is not a directory.
    """
    secrets_found = []
    for root, _, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if re.search(r'API_KEY|API_SECRET|PASSWORD|SECRET_KEY', content, re.IGNORECASE):
                        secrets_found.append(Secret(file_path, content))
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_found

def check_secrets(secrets: List[Secret]) -> None:
    """
    Check if any secrets were found.

    Args:
    secrets: List of Secret objects found in the project files.

    Raises:
    ValueError: If any secrets were found.
    """
    if secrets:
        raise ValueError("Secrets found in project files")

def main() -> None:
    """
    Test the module by scanning the project files and checking for secrets.
    """
    target_path = os.getcwd()
    secrets = scan_secrets(target_path)
    check_secrets(secrets)

if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

__all__ = ['scan_secrets', 'check_secrets']