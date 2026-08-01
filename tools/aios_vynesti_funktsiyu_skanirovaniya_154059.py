# tools/aios_vynesti_funktsiyu_skanirovaniya_154059.py

"""
Module for scanning TODO/FIXME/HACK comments in Python files.
"""

import os
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass for storing comment information."""
    path: str
    line_number: int
    comment_type: str
    comment_text: str

def scan_comments(path: str) -> List[Comment]:
    """
    Scan a Python file for TODO/FIXME/HACK comments.

    Args:
    path (str): Path to the Python file.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    comments = []
    try:
        with open(path, 'r') as file:
            for line_number, line in enumerate(file, start=1):
                for comment_type in ['TODO', 'FIXME', 'HACK']:
                    if comment_type in line:
                        comment_text = line.strip().split(comment_type)[1].strip()
                        comments.append(Comment(path, line_number, comment_type, comment_text))
    except FileNotFoundError:
        print(f"File '{path}' not found.")
    except Exception as e:
        print(f"Error scanning file '{path}': {e}")
    return comments

def scan_directory(directory: str) -> List[Comment]:
    """
    Scan a directory for TODO/FIXME/HACK comments in Python files.

    Args:
    directory (str): Path to the directory.

    Returns:
    List[Comment]: List of comments found in the directory.
    """
    comments = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                comments.extend(scan_comments(file_path))
    return comments

def main():
    """
    Entry point for testing the scanner.
    """
    directory = 'path/to/directory'
    comments = scan_directory(directory)
    for comment in comments:
        print(f"{comment.path}:{comment.line_number} - {comment.comment_type}: {comment.comment_text}")

if __name__ == '__main__':
    main()

__all__ = ['scan_comments', 'scan_directory']