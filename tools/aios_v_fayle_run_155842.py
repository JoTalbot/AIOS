"""
Module for scanning files for TODO, FIXME, and HACK comments.
"""

import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass for storing comment information."""
    file_path: str
    line_number: int
    comment_type: str

def scan_comments(target_path: str) -> List[Comment]:
    """
    Scan files in the target path for TODO, FIXME, and HACK comments.

    Args:
    target_path: Path to the directory to scan.

    Returns:
    List of Comment dataclasses containing file path, line number, and comment type.
    """
    comments = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'r') as f:
                for line_number, line in enumerate(f, start=1):
                    match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
                    if match:
                        comments.append(Comment(file_path, line_number, match.group(1)))
    return comments

def main():
    target_path = 'tools/aios_v_fayle_run_155842.py'
    comments = scan_comments(target_path)
    for comment in comments:
        print(f"File: {comment.file_path}, Line: {comment.line_number}, Comment: {comment.comment_type}")

if __name__ == '__main__':
    main()
    __all__ = ['scan_comments']