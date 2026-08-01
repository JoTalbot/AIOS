import subprocess
import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class BanditReport:
    """Bandit scan report."""
    vulnerabilities: list
    version: str

def run_bandit_scan(target_path: str) -> Optional[BanditReport]:
    """
    Run bandit scan on the target path.

    Args:
    target_path (str): Path to scan.

    Returns:
    Optional[BanditReport]: Scan report if successful, otherwise None.
    """
    try:
        # Run bandit scan
        output = subprocess.check_output(['bandit', '-r', target_path, '-l', 'json', '-o', 'bandit_report.json'])
        # Load scan report from JSON file
        with open('bandit_report.json', 'r') as f:
            report = json.load(f)
        # Create BanditReport object
        return BanditReport(vulnerabilities=report['vulnerabilities'], version=report['version'])
    except subprocess.CalledProcessError as e:
        # Handle scan failure
        print(f"Bandit scan failed with error code {e.returncode}")
        return None
    except json.JSONDecodeError as e:
        # Handle JSON decoding error
        print(f"Failed to parse bandit report: {e}")
        return None

def main():
    """Run bandit scan on the current directory."""
    target_path = '.'
    report = run_bandit_scan(target_path)
    if report:
        print("Bandit scan report:")
        print(f"Version: {report.version}")
        for vulnerability in report.vulnerabilities:
            print(f"  - {vulnerability['name']} (severity: {vulnerability['severity']})")

if __name__ == '__main__':
    main()

__all__ = ['run_bandit_scan']