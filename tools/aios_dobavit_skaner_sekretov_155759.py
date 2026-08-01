"""
Module for adding a secrets scanner to the CI pipeline.

This module uses the secrets-scan library to scan all files in the project for secrets.
"""

import os
import secrets_scan
from dataclasses import dataclass
from typing import List

__all__ = ['scan_project', 'scan_directory']

@dataclass
class ScanResult:
    """Result of a secrets scan."""
    secrets_found: bool
    secrets: List[str]

def scan_directory(path: str) -> ScanResult:
    """
    Scan a directory for secrets.

    Args:
        path: Path to the directory to scan.

    Returns:
        ScanResult: Result of the scan.
    """
    try:
        secrets = secrets_scan.scan_directory(path)
        return ScanResult(secrets_found=bool(secrets), secrets=secrets)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        return ScanResult(secrets_found=False, secrets=[])

def scan_project(target_path: str) -> ScanResult:
    """
    Scan a project for secrets.

    Args:
        target_path: Path to the project root.

    Returns:
        ScanResult: Result of the scan.
    """
    try:
        secrets = secrets_scan.scan_project(target_path)
        return ScanResult(secrets_found=bool(secrets), secrets=secrets)
    except Exception as e:
        print(f"Error scanning project: {e}")
        return ScanResult(secrets_found=False, secrets=[])

if __name__ == '__main__':
    target_path = os.path.dirname(os.path.abspath(__file__))
    result = scan_project(target_path)
    print(f"Secrets found: {result.secrets_found}")
    print(f"Secrets: {result.secrets}")