from dataclasses import dataclass
from pathlib import Path
from typing import List
from secrets_scanner import SecretsScanner

__all__ = ['scan_secrets']

@dataclass
class DetectedSecret:
    """Dataclass to represent a detected secret."""
    path: Path
    secret: str

def scan_secrets(target_path: Path) -> List[DetectedSecret]:
    """
    Scan the project for secrets using the secrets_scanner library.

    Args:
    target_path: The path to the project root.

    Returns:
    A list of DetectedSecret objects containing the path and secret.
    """
    try:
        scanner = SecretsScanner()
        secrets = scanner.scan(target_path)
        return [DetectedSecret(path=Path(secret.path), secret=secret.secret) for secret in secrets]
    except Exception as e:
        print(f"Error scanning secrets: {e}")
        return []

def main():
    target_path = Path('tools/aios_dobavit_funktsiyu_dlya_162505.py')
    secrets = scan_secrets(target_path)
    if secrets:
        print("Detected secrets:")
        for secret in secrets:
            print(f"Path: {secret.path}, Secret: {secret.secret}")
    else:
        print("No secrets detected.")

if __name__ == '__main__':
    main()