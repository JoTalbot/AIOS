"""
Module for scanning repository for TODO/FIXME/HACK comments.

Author: AIOS MetaCognitiveCoder
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

def scan_comments_in_file(file_path: str) -> List[Comment]:
    """
    Scan a single file for TODO/FIXME/HACK comments.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r'^(TODO|FIXME|HACK)', line)
                if match:
                    comments.append(Comment(file_path, i, match.group(1)))
            return comments
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def scan_repository(root_path: str) -> List[Comment]:
    """
    Scan a repository for TODO/FIXME/HACK comments.

    Args:
    root_path (str): Path to the repository root.

    Returns:
    List[Comment]: List of comments found in the repository.
    """
    comments = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = os.path.join(root, file)
            comments.extend(scan_comments_in_file(file_path))
    return comments

def main():
    """
    Test the module by scanning the current repository.
    """
    root_path = os.getcwd()
    comments = scan_repository(root_path)
    for comment in comments:
        print(f"File: {comment.file_path}, Line: {comment.line_number}, Comment: {comment.comment_type}")

if __name__ == '__main__':
    main()

__all__ = ['scan_comments_in_file', 'scan_repository']