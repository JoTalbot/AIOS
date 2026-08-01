"""
Tools for reading and fixing TODO and FIXME comments in code.

This module provides a function to read and fix TODO and FIXME comments in a given file.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class Comment:
    """Represents a TODO or FIXME comment."""
    text: str
    line_number: int

def read_comments(file_path: Path) -> List[Comment]:
    """
    Reads TODO and FIXME comments from a file.

    Args:
    file_path: Path to the file to read comments from.

    Returns:
    List of Comment objects containing the text and line number of each comment.
    """
    try:
        with file_path.open('r') as file:
            comments = []
            for line_number, line in enumerate(file, start=1):
                match = re.search(r'^(TODO|FIXME): (.*)$', line, re.MULTILINE)
                if match:
                    comments.append(Comment(match.group(2), line_number))
            return comments
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

def fix_comments(comments: List[Comment], file_path: Path) -> None:
    """
    Fixes TODO and FIXME comments in a file.

    Args:
    comments: List of Comment objects containing the text and line number of each comment.
    file_path: Path to the file to fix comments in.
    """
    try:
        with file_path.open('r') as file:
            lines = file.readlines()
        with file_path.open('w') as file:
            for line_number, line in enumerate(lines, start=1):
                for comment in comments:
                    if comment.line_number == line_number:
                        # Replace TODO or FIXME with a placeholder
                        lines[line_number - 1] = f"# {comment.text} (REMOVED)\n"
                file.write(lines[line_number - 1])
    except Exception as e:
        print(f"Error fixing file: {e}")

def main() -> None:
    """
    Tests the read_comments and fix_comments functions.
    """
    file_path = Path('example.txt')
    comments = read_comments(file_path)
    print("Comments:")
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.text}")
    fix_comments(comments, file_path)

if __name__ == '__main__':
    main()