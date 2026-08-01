import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ['find_secrets']

@dataclass
class Secret:
    """Data class representing a secret."""
    name: str
    value: str

def find_secrets(target_path: str) -> List[Secret]:
    """
    Scans all files in the target directory and its subdirectories for secrets.

    Args:
    target_path: The path to the directory to scan.

    Returns:
    A list of Secret data classes containing the found secrets.
    """
    secrets = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Regular expressions to find common secrets
                    password_regex = r'password\s*=\s*[\'"]?([a-zA-Z0-9]+)[\'"]?'
                    api_key_regex = r'api_key\s*=\s*[\'"]?([a-zA-Z0-9]+)[\'"]?'
                    secret_regex = r'secret\s*=\s*[\'"]?([a-zA-Z0-9]+)[\'"]?'
                    # Find matches
                    password_matches = re.findall(password_regex, content)
                    api_key_matches = re.findall(api_key_regex, content)
                    secret_matches = re.findall(secret_regex, content)
                    # Add matches to secrets list
                    secrets.extend([Secret('Password', match) for match in password_matches])
                    secrets.extend([Secret('API Key', match) for match in api_key_matches])
                    secrets.extend([Secret('Secret', match) for match in secret_matches])
            except Exception as e:
                # Handle exceptions when reading files
                print(f"Error reading file {file_path}: {e}")
    return secrets

if __name__ == '__main__':
    target_path = 'tools'
    secrets = find_secrets(target_path)
    print("Found secrets:")
    for secret in secrets:
        print(f"{secret.name}: {secret.value}")