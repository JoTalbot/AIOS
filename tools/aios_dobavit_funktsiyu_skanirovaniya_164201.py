"""
Module for scanning secrets in a project.

This module uses the secrets-scan library to scan for secrets in the project.
"""

import os
from dataclasses import dataclass
from typing import List
from secrets_scan import SecretsScan

__all__ = ['scan_secrets']

@dataclass
class ScanResult:
    """Result of the secret scan."""
    path: str
    secret: str

def scan_secrets(target_path: str) -> List[ScanResult]:
    """
    Scan for secrets in the project.

    Args:
    target_path: Path to the directory to scan.

    Returns:
    List of ScanResult objects containing the path and secret found.
    """
    try:
        scanner = SecretsScan()
        results = []
        for root, dirs, files in os.walk(target_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    secret = scanner.scan_file(file_path)
                    if secret:
                        results.append(ScanResult(path=file_path, secret=secret))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
        return results
    except Exception as e:
        print(f"Error scanning directory {target_path}: {e}")
        return []

if __name__ == '__main__':
    target_path = 'tools/aios_dobavit_funktsiyu_skanirovaniya_164201.py'
    results = scan_secrets(target_path)
    for result in results:
        print(f"Secret found in {result.path}: {result.secret}")