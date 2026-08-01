import re
import os
from dataclasses import dataclass
from typing import List, Optional

__all__ = ['scan_repository', 'remove_comments']

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    text: str

def remove_comments(file_path: str) -> None:
    """
    Remove TODO, FIXME, and HACK comments from a file.

    Args:
    file_path (str): Path to the file to remove comments from.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        cleaned_lines = []
        for i, line in enumerate(lines, start=1):
            match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
            if match:
                continue
            cleaned_lines.append(line)
        with open(file_path, 'w') as file:
            file.writelines(cleaned_lines)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def scan_repository(root_dir: str) -> List[Comment]:
    """
    Scan a repository for TODO, FIXME, and HACK comments.

    Args:
    root_dir (str): Path to the repository root directory.

    Returns:
    List[Comment]: List of comments found in the repository.
    """
    comments = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as file:
                        lines = file.readlines()
                    for i, line in enumerate(lines, start=1):
                        match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
                        if match:
                            comments.append(Comment(i, match.group(0).strip()))
                except Exception as e:
                    print(f"An error occurred while scanning {file_path}: {e}")
    return comments

if __name__ == '__main__':
    root_dir = 'path_to_your_repository_root'
    remove_comments(os.path.join(root_dir, 'file_to_remove_comments_from.py'))
    comments = scan_repository(root_dir)
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.text}")