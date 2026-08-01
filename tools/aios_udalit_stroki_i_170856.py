import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    comment_type: str
    comment_text: str

def scan_comments(target_path: str) -> List[Comment]:
    """
    Scan files in the target path for TODO/FIXME/HACK comments and return a list of found comments.

    Args:
    target_path: Path to the directory to scan.

    Returns:
    List of Comment dataclasses containing the line number, comment type, and comment text.
    """
    comments = []
    for root, _, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines, start=1):
                            match = re.search(r'#\s*(TODO|FIXME|HACK):?\s*(.*)', line)
                            if match:
                                comments.append(Comment(i, match.group(1), match.group(2).strip()))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
    return comments

__all__ = ['Comment', 'scan_comments']

if __name__ == '__main__':
    target_path = 'tools'
    comments = scan_comments(target_path)
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.comment_type} - {comment.comment_text}")