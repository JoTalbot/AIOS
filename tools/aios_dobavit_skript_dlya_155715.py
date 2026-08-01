"""
Module for scanning secrets in CI pipeline using secrets-scan library.

Usage:
    1. Install secrets-scan library: `pip install secrets-scan`
    2. Add this script to your CI pipeline (e.g. .gitlab-ci.yml or .github/workflows/main.yml)
    3. Run the script to scan for secrets in your project files
"""

import os
import sys
from dataclasses import dataclass
from typing import List
from secrets_scan import SecretsScan

__all__ = ['scan_secrets']

@dataclass
class ScanResult:
    """Result of secrets scan"""
    secrets: List[str]
    files: List[str]

def scan_secrets(target_path: str) -> ScanResult:
    """
    Scan for secrets in files in the target path.

    Args:
        target_path (str): Path to scan for secrets

    Returns:
        ScanResult: Result of secrets scan
    """
    try:
        scanner = SecretsScan()
        secrets = scanner.scan(target_path)
        files = [os.path.relpath(file, start=target_path) for file in secrets.keys()]
        return ScanResult(secrets=secrets, files=files)
    except Exception as e:
        print(f"Error scanning secrets: {e}")
        return ScanResult(secrets={}, files=[])

def main():
    """Run the script to scan for secrets in the project files"""
    target_path = os.getcwd()
    result = scan_secrets(target_path)
    print("Secrets found:")
    for file in result.files:
        print(f"  - {file}:")
        for secret in result.secrets.get(file, []):
            print(f"    - {secret}")

if __name__ == '__main__':
    main()