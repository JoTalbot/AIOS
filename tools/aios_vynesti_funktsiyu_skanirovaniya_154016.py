# tools/aios_vynesti_funktsiyu_skanirovaniya_154016.py

"""
Module for scanning TODO/FIXME/HACK comments in Python files.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Comment:
    """Dataclass for storing comment information."""
    line_number: int
    comment_type: str
    comment_text: str

def scan_comments(file_path: str) -> List[Comment]:
    """
    Scan a Python file for TODO/FIXME/HACK comments.

    Args:
    file_path (str): Path to the Python file to scan.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            comments = []
            for line_number, line in enumerate(file, start=1):
                for comment_type in ['TODO', 'FIXME', 'HACK']:
                    if comment_type in line:
                        comments.append(Comment(line_number, comment_type, line.strip()))
            return comments
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error scanning file '{file_path}': {e}")
        return []

def main():
    """
    Test the scan_comments function.
    """
    file_path = 'path_to_your_python_file.py'  # replace with your file path
    comments = scan_comments(file_path)
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.comment_type} - {comment.comment_text}")

if __name__ == '__main__':
    main()

__all__ = ['scan_comments']