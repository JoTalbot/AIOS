import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ['find_secrets']

@dataclass
class Secret:
    """Dataclass representing a secret found in a file."""
    file_path: str
    secret_type: str
    secret_value: str

def find_secrets(target_path: str) -> List[Secret]:
    """
    Scans all files in the target path and its subdirectories for secrets.

    Args:
    target_path: The path to scan for secrets.

    Returns:
    A list of Secret dataclasses containing the file path, secret type, and secret value.
    """
    secrets = []
    for root, _, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Regular expressions to match common secrets
                    password_regex = r'password\s*=\s*[\'"]?([^\'"]*)[\'"]?'
                    api_key_regex = r'api_key\s*=\s*[\'"]?([^\'"]*)[\'"]?'
                    secret_regex = r'secret\s*=\s*[\'"]?([^\'"]*)[\'"]?'
                    if re.search(password_regex, content):
                        secret_type = 'Password'
                        secret_value = re.search(password_regex, content).group(1)
                        secrets.append(Secret(file_path, secret_type, secret_value))
                    elif re.search(api_key_regex, content):
                        secret_type = 'API Key'
                        secret_value = re.search(api_key_regex, content).group(1)
                        secrets.append(Secret(file_path, secret_type, secret_value))
                    elif re.search(secret_regex, content):
                        secret_type = 'Secret'
                        secret_value = re.search(secret_regex, content).group(1)
                        secrets.append(Secret(file_path, secret_type, secret_value))
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
    return secrets

if __name__ == '__main__':
    target_path = 'tools'
    secrets = find_secrets(target_path)
    if secrets:
        print("Found secrets:")
        for secret in secrets:
            print(f"File: {secret.file_path}, Type: {secret.secret_type}, Value: {secret.secret_value}")
    else:
        print("No secrets found.")