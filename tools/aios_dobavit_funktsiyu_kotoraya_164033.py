import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Secret:
    """Class to represent a secret."""
    name: str
    value: str

def scan_secrets(path: str) -> List[Secret]:
    """
    Scans the given path for secrets.

    Args:
    path (str): The path to scan.

    Returns:
    List[Secret]: A list of secrets found.
    """
    secrets = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(('.env', '.ini', '.config')):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        for match in re.finditer(r'(?<=^|(?<=[\r\n]))(?P<key>[^:=]+)=(?P<value>[^:=]+)(?=$|(?=[\r\n]))', content, re.MULTILINE):
                            key = match.group('key').strip()
                            value = match.group('value').strip()
                            if key in ['password', 'api_key', 'token']:
                                secrets.append(Secret(key, value))
                except Exception as e:
                    print(f"Error processing file {file}: {e}")
    return secrets

__all__ = ['scan_secrets']

if __name__ == '__main__':
    path = 'tools'
    secrets = scan_secrets(path)
    if secrets:
        print("Found secrets:")
        for secret in secrets:
            print(f"{secret.name}: {secret.value}")
    else:
        print("No secrets found.")