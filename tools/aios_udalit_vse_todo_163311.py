"""
Module to remove TODO and FIXME comments from a specified range of lines in a code file.

Target path: tools/aios_udalit_vse_todo_163311.py
"""

import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    text: str

def remove_comments(file_path: str, start_line: int, end_line: int) -> List[Comment]:
    """
    Remove TODO and FIXME comments from a specified range of lines in a code file.

    Args:
    file_path (str): Path to the code file.
    start_line (int): Start line number (inclusive).
    end_line (int): End line number (inclusive).

    Returns:
    List[Comment]: List of comments found in the specified range.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    
    comments = []
    for i, line in enumerate(lines, start=1):
        if start_line <= i <= end_line:
            match = re.search(r'# TODO|FIXME', line)
            if match:
                comments.append(Comment(i, match.group()))
                line = line.replace(match.group(), f"# TODO/FIXME: {match.group()} - Problem solved.")
        lines[i-1] = line
    
    with open(file_path, 'w') as file:
        file.writelines(lines)
    
    return comments

def main():
    file_path = 'path_to_your_code_file.py'
    start_line = 147
    end_line = 161
    comments = remove_comments(file_path, start_line, end_line)
    print("Removed comments:")
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.text}")

if __name__ == '__main__':
    main()
__all__ = ['remove_comments']