import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ["find_todo_comments", "scan_repository"]

@dataclass
class TodoComment:
    """Dataclass to represent a TODO/FIXME/HACK comment."""
    file_path: str
    line_number: int
    comment: str

def find_todo_comments(file_path: str) -> List[TodoComment]:
    """
    Find TODO/FIXME/HACK comments in a given file.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[TodoComment]: List of TODO/FIXME/HACK comments found in the file.
    """
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r"TODO|FIXME|HACK", line, re.IGNORECASE)
                if match:
                    comments.append(TodoComment(file_path, i, line.strip()))
            return comments
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def scan_repository(target_path: str) -> List[TodoComment]:
    """
    Scan a repository and find TODO/FIXME/HACK comments.

    Args:
    target_path (str): Path to the repository root.

    Returns:
    List[TodoComment]: List of TODO/FIXME/HACK comments found in the repository.
    """
    try:
        comments = []
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    comments.extend(find_todo_comments(file_path))
        return comments
    except Exception as e:
        print(f"Error scanning repository: {e}")
        return []

def main():
    """Run the script."""
    target_path = "tools"
    comments = scan_repository(target_path)
    if comments:
        print("TODO/FIXME/HACK comments found:")
        for comment in comments:
            print(f"{comment.file_path}:{comment.line_number} - {comment.comment}")
    else:
        print("No TODO/FIXME/HACK comments found.")

if __name__ == "__main__":
    main()