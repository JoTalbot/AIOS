# tools/secrets.py

import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Represents a secret found in a file."""
    path: str
    value: str

def find_secrets(root_path: str) -> List[Secret]:
    """
    Scans all files in the project and identifies secrets.

    Args:
    root_path (str): The root path of the project to scan.

    Returns:
    List[Secret]: A list of secrets found in the project.
    """
    secrets = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Regular expression pattern to match secrets
                    pattern = r"(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|API_KEY)=([a-zA-Z0-9]+)"
                    matches = re.findall(pattern, content)
                    for match in matches:
                        secret = Secret(file_path, match[1])
                        secrets.append(secret)
            except Exception as e:
                # Handle exceptions when reading files
                print(f"Error reading file {file_path}: {str(e)}")
    return secrets

if __name__ == '__main__':
    # Test the function
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    secrets = find_secrets(root_path)
    for secret in secrets:
        print(f"Secret found in {secret.path}: {secret.value}")