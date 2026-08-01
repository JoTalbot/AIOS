"""
Module for scanning TODO/FIXME/HACK comments in Python files.

This module provides a function to scan Python files for TODO/FIXME/HACK comments
and return a list of found comments.

Author: AIOS MetaCognitiveCoder
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    comment: str

def scan_comments(file_path: Path) -> List[Comment]:
    """
    Scan a Python file for TODO/FIXME/HACK comments.

    Args:
    file_path: Path to the Python file to scan.

    Returns:
    List of Comment objects containing the line number and comment text.
    """
    try:
        with file_path.open('r', encoding='utf-8') as file:
            comments = []
            for line_number, line in enumerate(file, start=1):
                match = re.search(r'#\s*(TODO|FIXME|HACK):?\s*(.*)', line)
                if match:
                    comments.append(Comment(line_number, match.group(2).strip()))
            return comments
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def main():
    """
    Test the scan_comments function.

    Scans the current directory for Python files and prints the found comments.
    """
    import os
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                comments = scan_comments(file_path)
                if comments:
                    print(f"File: {file_path}")
                    for comment in comments:
                        print(f"Line {comment.line_number}: {comment.comment}")
                    print()

if __name__ == '__main__':
    main()

__all__ = ['scan_comments']