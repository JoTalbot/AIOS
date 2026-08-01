import os
import re
from dataclasses import dataclass
from typing import List, Tuple

__all__ = ['find_comments']

@dataclass
class Comment:
    """Dataclass to represent a found comment."""
    file: str
    line: int
    comment: str

def find_comments(target_path: str) -> List[Comment]:
    """
    Scan all Python files in the target directory and find comments with TODO, FIXME, HACK, XXX, BUG keywords.

    Args:
    target_path (str): Path to the target directory.

    Returns:
    List[Comment]: List of found comments with file and line information.
    """
    comments = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        for num, line in enumerate(f, 1):
                            match = re.search(r'#\s*(TODO|FIXME|HACK|XXX|BUG)', line)
                            if match:
                                comments.append(Comment(file, num, match.group()))
                except Exception as e:
                    print(f"Error processing file {file}: {e}")
    return comments

def main():
    target_path = 'tools'
    comments = find_comments(target_path)
    for comment in comments:
        print(f"File: {comment.file}, Line: {comment.line}, Comment: {comment.comment}")

if __name__ == '__main__':
    main()