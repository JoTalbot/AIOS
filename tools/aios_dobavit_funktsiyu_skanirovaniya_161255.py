import os
import secrets
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Dataclass representing a secret."""
    name: str
    value: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan files in the target path for secrets and return a list of found secrets.

    Args:
    target_path (str): Path to scan for secrets.

    Returns:
    List[Secret]: List of found secrets.
    """
    secrets_list = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    for secret in secrets.extractor().find_all(content):
                        secrets_list.append(Secret(name=file, value=secret))
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_list

def main():
    """Test the scan_secrets function."""
    target_path = 'tools'
    secrets_found = scan_secrets(target_path)
    if secrets_found:
        print("Found secrets:")
        for secret in secrets_found:
            print(f"Name: {secret.name}, Value: {secret.value}")
    else:
        print("No secrets found.")

if __name__ == '__main__':
    main()