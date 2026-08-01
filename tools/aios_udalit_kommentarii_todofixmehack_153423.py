"""
Module for scanning repository for TODO/FIXME/HACK comments and removing them.

Target path: tools/aios_udalit_kommentarii_todofixmehack_153423.py
"""

import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass for storing comment information."""
    line_number: int
    comment: str

def scan_repository(path: str) -> List[Comment]:
    """
    Scan the repository for TODO/FIXME/HACK comments.

    Args:
    path (str): Path to the repository root.

    Returns:
    List[Comment]: List of comments found in the repository.
    """
    comments = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        for line_number, line in enumerate(f, start=1):
                            if re.search(r"TODO|FIXME|HACK", line, re.IGNORECASE):
                                comments.append(Comment(line_number, line.strip()))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
    return comments

def remove_comments(comments: List[Comment], path: str) -> None:
    """
    Remove TODO/FIXME/HACK comments from the repository.

    Args:
    comments (List[Comment]): List of comments to remove.
    path (str): Path to the repository root.
    """
    for comment in comments:
        file_path = os.path.join(path, f"{comment.line_number}.py")
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
            with open(file_path, "w") as f:
                for line in lines:
                    if comment.line_number != int(line.split(":")[0]):
                        f.write(line)
        except Exception as e:
            print(f"Error removing comment {comment.comment}: {e}")

def main() -> None:
    """
    Main function for testing the module.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    comments = scan_repository(path)
    print("Found comments:")
    for comment in comments:
        print(f"{comment.line_number}: {comment.comment}")
    remove_comments(comments, path)

if __name__ == "__main__":
    main()
    __all__ = ["Comment", "scan_repository", "remove_comments"]