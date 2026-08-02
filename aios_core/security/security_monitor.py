# aios_core/security/security_monitor.py
"""Security monitoring module for regular vulnerability scanning in CI pipeline."""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from aios_core.self_protection import PROTECTED_PATTERNS

@dataclass
class Vulnerability:
    """Data class representing a detected vulnerability."""
    file_path: str
    line_number: int
    vulnerability_type: str
    description: str
    severity: str = "medium"

class SecurityMonitor:
    """Main security monitoring class for scanning vulnerabilities in codebase."""

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize SecurityMonitor with optional repository path.

        Args:
            repo_path: Path to repository. If None, uses current directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.vulnerabilities: List[Vulnerability] = []

    def scan_for_hardcoded_secrets(self) -> List[Vulnerability]:
        """Scan repository for hardcoded secrets using protected patterns.

        Returns:
            List of detected vulnerabilities
        """
        self.vulnerabilities = []

        # Compile patterns from self_protection.py
        patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in PROTECTED_PATTERNS
        ]

        # Walk through repository files
        for file_path in self._get_repo_files():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if pattern.search(line):
                            self.vulnerabilities.append(
                                Vulnerability(
                                    file_path=str(file_path),
                                    line_number=line_num,
                                    vulnerability_type="hardcoded_secret",
                                    description=f"Potential secret detected matching pattern: {pattern.pattern[:50]}...",
                                    severity="high"
                                )
                            )
                            break
            except Exception as e:
                self.vulnerabilities.append(
                    Vulnerability(
                        file_path=str(file_path),
                        line_number=0,
                        vulnerability_type="scan_error",
                        description=f"Failed to scan file: {str(e)}",
                        severity="low"
                    )
                )

        return self.vulnerabilities

    def check_vulnerable_patterns(self) -> List[Vulnerability]:
        """Check for dangerous code patterns like eval(), exec(), unsafe imports.

        Returns:
            List of detected vulnerabilities
        """
        self.vulnerabilities = []

        dangerous_patterns = [
            (re.compile(r'eval\s*\('), "eval() function usage"),
            (re.compile(r'exec\s*\('), "exec() function usage"),
            (re.compile(r'import\s+os\s*;'), "Potentially unsafe import"),
            (re.compile(r'pickle\.load\s*\('), "Unsafe pickle usage"),
            (re.compile(r'subprocess\.Popen\s*\('), "subprocess usage"),
            (re.compile(r'__import__\s*\('), "Dynamic import"),
        ]

        for file_path in self._get_repo_files():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern, desc in dangerous_patterns:
                        if pattern.search(line):
                            self.vulnerabilities.append(
                                Vulnerability(
                                    file_path=str(file_path),
                                    line_number=line_num,
                                    vulnerability_type="dangerous_pattern",
                                    description=desc,
                                    severity="high"
                                )
                            )
            except Exception as e:
                self.vulnerabilities.append(
                    Vulnerability(
                        file_path=str(file_path),
                        line_number=0,
                        vulnerability_type="scan_error",
                        description=f"Failed to scan file: {str(e)}",
                        severity="low"
                    )
                )

        return self.vulnerabilities

    def generate_report(self, output_path: Optional[str] = None) -> Dict:
        """Generate security report in JSON format.

        Args:
            output_path: Optional path to save report. If None, returns dict.

        Returns:
            Dictionary with report data or saves to file
        """
        report = {
            "metadata": {
                "timestamp": os.getenv("CI_RUN_ID", "local"),
                "repository": str(self.repo_path),
                "scan_types": ["hardcoded_secrets", "dangerous_patterns"]
            },
            "summary": {
                "total_vulnerabilities": len(self.vulnerabilities),
                "by_severity": {
                    "high": sum(1 for v in self.vulnerabilities if v.severity == "high"),
                    "medium": sum(1 for v in self.vulnerabilities if v.severity == "medium"),
                    "low": sum(1 for v in self.vulnerabilities if v.severity == "low")
                }
            },
            "vulnerabilities": [
                {
                    "file_path": v.file_path,
                    "line_number": v.line_number,
                    "type": v.vulnerability_type,
                    "description": v.description,
                    "severity": v.severity
                }
                for v in self.vulnerabilities
            ]
        }

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _get_repo_files(self) -> List[Path]:
        """Get all relevant files in repository for scanning.

        Returns:
            List of Path objects to files to scan
        """
        files = []
        for root, _, filenames in os.walk(self.repo_path):
            for filename in filenames:
                if filename.endswith(('.py', '.env', '.yaml', '.yml', '.json', '.toml', '.ini')):
                    files.append(Path(root) / filename)
        return files

def main() -> None:
    """CLI interface for security monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="Security vulnerability scanner")
    parser.add_argument("--path", type=str, default=".",
                       help="Path to repository to scan")
    parser.add_argument("--output", type=str, default="security_report.json",
                       help="Output file for report")

    args = parser.parse_args()

    monitor = SecurityMonitor(args.path)
    monitor.scan_for_hardcoded_secrets()
    monitor.check_vulnerable_patterns()
    report = monitor.generate_report(args.output)

    print(f"Scan completed. Found {report['summary']['total_vulnerabilities']} vulnerabilities.")
    print(f"Report saved to: {args.output}")

if __name__ == "__main__":
    main()