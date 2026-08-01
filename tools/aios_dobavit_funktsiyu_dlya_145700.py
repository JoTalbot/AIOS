"""
Module for scanning code for TODO/FIXME/HACK comments and reporting found issues.

Usage:
    - Run as a script to scan the current directory and its subdirectories.
    - Pass a directory path as an argument to scan a specific directory.
"""

import os
import sys
from pylint import epylint as lint
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['scan_code']

@dataclass
class Issue:
    """Represents a found issue."""
    line: int
    message: str

def scan_code(path: str = '.') -> List[Issue]:
    """
    Scans the code in the given directory and its subdirectories for TODO/FIXME/HACK comments.

    Args:
        path: The directory path to scan. Defaults to the current directory.

    Returns:
        A list of found issues.
    """
    try:
        # Run pylint on the given directory
        report = lint.py_run(path, None, None)
        # Parse the pylint report
        issues = []
        for line in report.splitlines():
            if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
                # Extract the issue line and message
                issue_line, issue_message = line.split(':', 1)
                issue_line = int(issue_line.split(':')[0])
                issue_message = issue_message.strip()
                issues.append(Issue(issue_line, issue_message))
        return issues
    except Exception as e:
        # Handle any exceptions that occur during scanning
        print(f"Error scanning code: {e}")
        return []

def main():
    # Get the target directory path from the command line arguments
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = '.'
    # Scan the code and print the found issues
    issues = scan_code(path)
    if issues:
        print("Found issues:")
        for issue in issues:
            print(f"Line {issue.line}: {issue.message}")
    else:
        print("No issues found.")

if __name__ == '__main__':
    main()