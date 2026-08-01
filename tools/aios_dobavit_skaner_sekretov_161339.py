"""
Module for scanning secrets in project files.

This module uses the `python-decouple` library to store and scan secrets.
"""

import os
from decouple import config, Repository
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Dataclass for storing secret information."""
    name: str
    value: str

class SecretScanner:
    """Class for scanning secrets in project files."""

    def __init__(self, target_path: str):
        self.target_path = target_path
        self.secrets = Repository()

    def scan_for_tags(self) -> List[Secret]:
        """
        Scan all files in the project and identify secrets.

        Returns:
            List[Secret]: A list of identified secrets.
        """
        secrets_found = []
        for root, dirs, files in os.walk(self.target_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        for key, value in self.secrets.items():
                            if key in content:
                                secrets_found.append(Secret(key, value))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
        return secrets_found

def scan_for_tags(target_path: str) -> List[Secret]:
    """
    Scan all files in the project and identify secrets.

    Args:
        target_path (str): The path to the project root.

    Returns:
        List[Secret]: A list of identified secrets.
    """
    scanner = SecretScanner(target_path)
    return scanner.scan_for_tags()

if __name__ == '__main__':
    target_path = os.path.dirname(os.path.abspath(__file__))
    secrets = scan_for_tags(target_path)
    for secret in secrets:
        print(f"Secret found: {secret.name} = {secret.value}")