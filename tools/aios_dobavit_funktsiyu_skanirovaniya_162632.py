from dataclasses import dataclass
from typing import List, Dict
import os
import re

@dataclass
class Secret:
    """Class to represent a secret found in a file."""
    file_path: str
    secret: str

def scan_secrets(target_path: str) -> List[Secret]:
    """
    Scan the target path and its subdirectories for secrets.

    Args:
    target_path (str): The path to scan for secrets.

    Returns:
    List[Secret]: A list of secrets found in the target path.
    """
    secrets_found = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Regular expression to match common secrets (e.g., API keys, passwords)
                    pattern = r"(API_KEY|PASSWORD|SECRET_KEY)=([a-zA-Z0-9]+)"
                    matches = re.findall(pattern, content)
                    for match in matches:
                        secret = match[1]
                        secrets_found.append(Secret(file_path, secret))
            except Exception as e:
                # Handle exceptions when reading or parsing files
                print(f"Error processing file {file_path}: {str(e)}")
    return secrets_found

def report_secrets(secrets_found: List[Secret]) -> Dict[str, List[str]]:
    """
    Generate a report of the secrets found.

    Args:
    secrets_found (List[Secret]): A list of secrets found.

    Returns:
    Dict[str, List[str]]: A dictionary with file paths as keys and lists of secrets as values.
    """
    report = {}
    for secret in secrets_found:
        if secret.file_path not in report:
            report[secret.file_path] = []
        report[secret.file_path].append(secret.secret)
    return report

def main():
    target_path = 'tools'
    secrets_found = scan_secrets(target_path)
    report = report_secrets(secrets_found)
    print("Secrets found:")
    for file_path, secrets in report.items():
        print(f"  {file_path}:")
        for secret in secrets:
            print(f"    - {secret}")

if __name__ == '__main__':
    main()
__all__ = ['scan_secrets', 'report_secrets']