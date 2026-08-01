import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class CodeIssue:
    """Represents a code issue found during scanning."""
    path: Path
    line_number: int
    issue_type: str
    issue_text: str

def scan_code_for_issues(target_path: Path) -> List[CodeIssue]:
    """
    Scans the code at the target path for TODO/FIXME/HACK comments.

    Args:
    target_path: The path to the code to scan.

    Returns:
    A list of CodeIssue objects found during scanning.
    """
    try:
        with open(target_path, 'r') as file:
            content = file.readlines()
    except FileNotFoundError:
        print(f"Error: File '{target_path}' not found.")
        return []

    issues = []
    for line_number, line in enumerate(content, start=1):
        if re.search(r'\b(TODO|FIXME|HACK)\b', line):
            issue_type = re.search(r'\b(TODO|FIXME|HACK)\b', line).group()
            issue_text = re.sub(r'\b(TODO|FIXME|HACK)\b', '', line).strip()
            issues.append(CodeIssue(target_path, line_number, issue_type, issue_text))

    return issues

def main():
    """Tests the scan_code_for_issues function."""
    target_path = Path('run_coder_orchestrator.py')
    issues = scan_code_for_issues(target_path)
    for issue in issues:
        print(f"Path: {issue.path}, Line Number: {issue.line_number}, Issue Type: {issue.issue_type}, Issue Text: {issue.issue_text}")

if __name__ == '__main__':
    main()

__all__ = ['scan_code_for_issues']