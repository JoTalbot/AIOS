"""
Module for removing TODO/FIXME/HACK comments from a given file.

Author: AIOS MetaCognitiveCoder
"""

import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass for storing TODO/FIXME/HACK comments."""
    text: str
    line_number: int

def remove_comments(file_path: str) -> None:
    """
    Removes TODO/FIXME/HACK comments from a given file.

    Args:
    file_path (str): Path to the file to be processed.

    Returns:
    None
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        comments = []
        for line_number, line in enumerate(lines, start=1):
            match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
            if match:
                comments.append(Comment(match.group(0), line_number))

        # Fixing the cycle for scanning TODO/FIXME/HACK comments
        for comment in comments:
            lines[comment.line_number - 1] = re.sub(r'#\s*(TODO|FIXME|HACK)', '', lines[comment.line_number - 1])

        with open(file_path, 'w') as file:
            file.writelines(lines)

    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def scan_comments(file_path: str) -> List[Comment]:
    """
    Scans a given file for TODO/FIXME/HACK comments.

    Args:
    file_path (str): Path to the file to be processed.

    Returns:
    List[Comment]: List of found comments.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        comments = []
        for line_number, line in enumerate(lines, start=1):
            match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
            if match:
                comments.append(Comment(match.group(0), line_number))

        return comments

    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == '__main__':
    import os
    import sys

    if len(sys.argv) != 2:
        print("Usage: python aios_udalit_todofixmehack_v_161711.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"File {file_path} not found.")
        sys.exit(1)

    remove_comments(file_path)
    comments = scan_comments(file_path)
    print("Found comments:")
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.text}")