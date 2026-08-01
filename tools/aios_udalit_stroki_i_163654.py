import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    text: str
    line_number: int

def scan_comments(file_path: str) -> List[Comment]:
    """
    Scan a file for TODO/FIXME/HACK comments and return a list of comments.

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
                match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
                if match:
                    comments.append(Comment(match.group(0), i))
            return comments
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def main():
    """Main function to test the script."""
    target_path = 'tools/aios_udalit_stroki_i_163654.py'
    comments = scan_comments(target_path)
    print("Comments found:")
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.text}")

if __name__ == '__main__':
    main()
__all__ = ['Comment', 'scan_comments']