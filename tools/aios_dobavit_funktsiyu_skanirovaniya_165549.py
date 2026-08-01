import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Data class representing a secret."""
    name: str
    value: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the project for secrets.

    Args:
    target_path (str): The path to scan for secrets.

    Returns:
    List[Secret]: A list of secrets found in the project.
    """
    secrets = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(('.env', '.ini', '.json', '.yaml', '.yml')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Regular expression patterns to match secrets
                        patterns = [
                            r'API_KEY=(.*)',
                            r'PASSWORD=(.*)',
                            r'SECRET_KEY=(.*)',
                            r'ACCESS_TOKEN=(.*)',
                            r'CLIENT_ID=(.*)',
                            r'CLIENT_SECRET=(.*)',
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, content)
                            if match:
                                secret_name = pattern.split('=')[0].strip()
                                secret_value = match.group(1).strip()
                                secrets.append(Secret(secret_name, secret_value))
                except Exception as e:
                    # Handle exceptions when reading or parsing files
                    print(f"Error processing file {file_path}: {str(e)}")
    return secrets

__all__ = ['scan_secrets']

if __name__ == '__main__':
    target_path = 'tools/aios_dobavit_funktsiyu_skanirovaniya_165549.py'
    secrets = scan_secrets(os.path.dirname(target_path))
    for secret in secrets:
        print(f"Secret: {secret.name} = {secret.value}")