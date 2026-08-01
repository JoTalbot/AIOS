import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Class to represent a secret."""
    name: str
    value: str

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
            if file.endswith(('.env', '.env.example')):
                with open(os.path.join(root, file), 'r') as f:
                    for line in f:
                        match = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
                        if match:
                            secret_name = match.group(1)
                            secret_value = match.group(2)
                            secrets.append(Secret(secret_name, secret_value))
            elif file.endswith(('.py', '.json', '.yaml', '.yml')):
                with open(os.path.join(root, file), 'r') as f:
                    content = f.read()
                    match = re.search(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*"(.*)"', content)
                    if match:
                        secret_name = match.group(1)
                        secret_value = match.group(2)
                        secrets.append(Secret(secret_name, secret_value))
    return secrets

__all__ = ['scan_secrets']

if __name__ == '__main__':
    target_path = os.path.dirname(os.path.abspath(__file__))
    secrets = scan_secrets(target_path)
    for secret in secrets:
        print(f"Secret: {secret.name} = {secret.value}")