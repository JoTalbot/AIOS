import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ['scan_repository']

@dataclass
class File:
    """Represents a file with a TODO/FIXME/HACK comment."""
    path: str
    comment_count: int

def scan_repository(root_dir: str) -> List[File]:
    """
    Scans a repository for TODO/FIXME/HACK comments in Python files.

    Args:
    root_dir (str): The root directory of the repository.

    Returns:
    List[File]: A list of files with TODO/FIXME/HACK comments.
    """
    try:
        files = []
        for root, dirs, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(root, filename)
                    with open(file_path, 'r') as file:
                        content = file.read()
                        comments = re.findall(r'#\s*(TODO|FIXME|HACK)', content, re.MULTILINE)
                        if comments:
                            files.append(File(file_path, len(comments)))
        return files
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

if __name__ == '__main__':
    root_dir = 'tools'
    files_with_comments = scan_repository(root_dir)
    if files_with_comments:
        print("Files with TODO/FIXME/HACK comments:")
        for file in files_with_comments:
            print(f"{file.path}: {file.comment_count} comments")
    else:
        print("No files with TODO/FIXME/HACK comments found.")