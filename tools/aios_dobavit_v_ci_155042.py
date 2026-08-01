"""
Module for adding truffleHog secret scanner to CI pipeline.

This module provides a self-contained implementation of truffleHog secret scanner.
It includes a function for scanning secrets and a main block for testing.

Author: MetaCognitiveCoder
"""

import os
import subprocess
from dataclasses import dataclass
from typing import List

@dataclass
class TruffleHogResult:
    """Result of truffleHog secret scanner."""
    secrets: List[str]
    total_lines: int

def scan_secrets(target_path: str) -> TruffleHogResult:
    """
    Scan the target path for secrets using truffleHog.

    Args:
        target_path: Path to scan for secrets.

    Returns:
        TruffleHogResult: Result of the secret scan.
    """
    try:
        # Run truffleHog command
        result = subprocess.run(
            ["truffleHog", target_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        # Parse output
        output = result.stdout.decode("utf-8").strip()
        secrets = output.splitlines()
        total_lines = sum(1 for line in secrets if line.startswith("Potential secret"))
        return TruffleHogResult(secrets, total_lines)
    except subprocess.CalledProcessError as e:
        # Handle truffleHog command failure
        print(f"Error running truffleHog: {e}")
        return TruffleHogResult([], 0)
    except Exception as e:
        # Handle other exceptions
        print(f"Error scanning secrets: {e}")
        return TruffleHogResult([], 0)

def main():
    """
    Test the truffleHog secret scanner.
    """
    target_path = "tools"
    result = scan_secrets(target_path)
    print(f"Secrets found: {result.secrets}")
    print(f"Total lines scanned: {result.total_lines}")

if __name__ == "__main__":
    main()

__all__ = ["scan_secrets"]