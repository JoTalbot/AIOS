import os
import re
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Secret:
    """Class to represent a secret found in a file."""
    file_path: str
    line_number: int
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan files in the target path for secrets.

    Args:
    target_path (str): Path to scan for secrets.

    Returns:
    List[Secret]: List of secrets found in the files.
    """
    secrets_found = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    for line_number, line in enumerate(f, start=1):
                        if re.search(r'API_KEY|API_SECRET|PASSWORD|SECRET_KEY', line, re.IGNORECASE):
                            secret = re.search(r'API_KEY|API_SECRET|PASSWORD|SECRET_KEY', line, re.IGNORECASE).group()
                            secrets_found.append(Secret(file_path, line_number, secret))
            except Exception as e:
                print(f"Error scanning file {file_path}: {str(e)}")
    return secrets_found

def main():
    """Main function to test the scan_secrets function."""
    target_path = 'tools'
    secrets = scan_secrets(target_path)
    if secrets:
        print("Secrets found:")
        for secret in secrets:
            print(f"File: {secret.file_path}, Line: {secret.line_number}, Secret: {secret.secret}")
    else:
        print("No secrets found.")

if __name__ == '__main__':
    main()

__all__ = ['scan_secrets']