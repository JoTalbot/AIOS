import re
import os
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    comment: str

def scan_comments(target_path: str) -> List[Comment]:
    """
    Scan a directory for Python files containing TODO/FIXME/HACK comments.

    Args:
    target_path: Path to the directory to scan.

    Returns:
    List of comments containing TODO/FIXME/HACK keywords.
    """
    comments = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        for line_number, line in enumerate(f, start=1):
                            match = re.search(r"(TODO|FIXME|HACK)", line, re.IGNORECASE)
                            if match:
                                comments.append(Comment(line_number, line.strip()))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
    return comments

__all__ = ["scan_comments"]

if __name__ == "__main__":
    target_path = "tools/aios_v_fayle_run_153634.py"
    comments = scan_comments(target_path)
    if comments:
        print("Comments containing TODO/FIXME/HACK keywords:")
        for comment in comments:
            print(f"Line {comment.line_number}: {comment.comment}")
    else:
        print("No comments containing TODO/FIXME/HACK keywords found.")