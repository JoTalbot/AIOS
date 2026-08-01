import re
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line: int
    text: str

def find_todo_comments(file_path: str) -> List[Comment]:
    """
    Find TODO comments in a file.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[Comment]: List of TODO comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return [Comment(i + 1, line.strip()) for i, line in enumerate(lines) if re.search(r'# TODO', line)]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def find_fixme_comments(file_path: str) -> List[Comment]:
    """
    Find FIXME comments in a file.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[Comment]: List of FIXME comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return [Comment(i + 1, line.strip()) for i, line in enumerate(lines) if re.search(r'# FIXME', line)]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def find_hack_comments(file_path: str) -> List[Comment]:
    """
    Find HACK comments in a file.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[Comment]: List of HACK comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return [Comment(i + 1, line.strip()) for i, line in enumerate(lines) if re.search(r'# HACK', line)]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def replace_comments(file_path: str) -> None:
    """
    Replace TODO, FIXME, and HACK comments with their corresponding functions.

    Args:
    file_path (str): Path to the file to modify.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            todo_comments = find_todo_comments(file_path)
            fixme_comments = find_fixme_comments(file_path)
            hack_comments = find_hack_comments(file_path)
            comments = todo_comments + fixme_comments + hack_comments
            for comment in comments:
                lines[comment.line - 1] = f"print(f'Comment found at line {comment.line}: {comment.text}')\n"
            with open(file_path, 'w') as file:
                file.writelines(lines)
    except Exception as e:
        print(f"An error occurred: {e}")

def main() -> None:
    """
    Test the functions.
    """
    target_path = 'tools/aios_udalit_kommentarii_todofixmehack_151948.py'
    replace_comments(target_path)

if __name__ == '__main__':
    main()

__all__ = ['find_todo_comments', 'find_fixme_comments', 'find_hack_comments', 'replace_comments']