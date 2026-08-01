# tools/aios_dobavit_ci_shag_152327.py

import os
import subprocess
from dataclasses import dataclass
from typing import List

__all__ = ["check_todo_fixme_hack"]

@dataclass
class ScanResult:
    """Result of the scan."""
    status: bool
    message: str

def scan_gitleaks() -> ScanResult:
    """Scan the repository using gitleaks."""
    try:
        output = subprocess.check_output(["gitleaks", "scan", "."]).decode("utf-8")
        if "No secrets found" in output:
            return ScanResult(status=True, message="No secrets found")
        else:
            return ScanResult(status=False, message=output)
    except subprocess.CalledProcessError as e:
        return ScanResult(status=False, message=f"Gitleaks scan failed with code {e.returncode}")

def scan_snyk() -> ScanResult:
    """Scan the repository using snyk."""
    try:
        output = subprocess.check_output(["snyk", "test", "."]).decode("utf-8")
        if "No vulnerabilities found" in output:
            return ScanResult(status=True, message="No vulnerabilities found")
        else:
            return ScanResult(status=False, message=output)
    except subprocess.CalledProcessError as e:
        return ScanResult(status=False, message=f"Snyk scan failed with code {e.returncode}")

def check_todo_fixme_hack() -> bool:
    """Check the repository for TODO/FIXME/HACK comments and fail if found."""
    try:
        output = subprocess.check_output(["git", "grep", "-r", "-E", "(TODO|FIXME|HACK)", "."]).decode("utf-8")
        if output:
            return False
        else:
            return True
    except subprocess.CalledProcessError:
        return True

def main() -> None:
    """Main function for testing."""
    if not check_todo_fixme_hack():
        print("Repository contains TODO/FIXME/HACK comments. Failing.")
        exit(1)
    else:
        print("Repository is clean.")

if __name__ == "__main__":
    main()