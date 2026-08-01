from dataclasses import dataclass
from pathlib import Path
import re
import sys

__all__ = ['CodeAnalyzer']

@dataclass
class CodeIssue:
    """Represents a code issue."""
    path: Path
    line: int
    message: str

class CodeAnalyzer:
    """Analyzes code for TODO/FIXME/HACK comments and generates a technical debt report."""

    def __init__(self, target_path: Path):
        """Initializes the code analyzer with a target path."""
        self.target_path = target_path

    def scan_code(self) -> list[CodeIssue]:
        """Scans the code for TODO/FIXME/HACK comments and returns a list of issues."""
        issues = []
        for file in self.target_path.rglob('*.py'):
            try:
                with file.open('r') as f:
                    for line_num, line in enumerate(f, start=1):
                        match = re.search(r'(?m)^# ?(?:TODO|FIXME|HACK):', line)
                        if match:
                            issues.append(CodeIssue(file, line_num, match.group(0).strip()))
            except Exception as e:
                print(f"Error scanning file {file}: {e}")
        return issues

    def generate_report(self, issues: list[CodeIssue]) -> str:
        """Generates a technical debt report from the list of issues."""
        report = "Technical Debt Report:\n"
        for issue in issues:
            report += f"{issue.path}: {issue.line} - {issue.message}\n"
        return report

def main():
    """Tests the code analyzer."""
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

    analyzer = CodeAnalyzer(target_path)
    issues = analyzer.scan_code()
    report = analyzer.generate_report(issues)

    print(report)

if __name__ == '__main__':
    main()