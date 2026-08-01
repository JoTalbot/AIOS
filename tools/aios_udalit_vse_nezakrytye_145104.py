import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Represents a comment with a tag."""
    tag: str
    text: str

def find_comments(file_path: str) -> List[Comment]:
    """
    Finds all TODO/FIXME/HACK comments in the given file.

    Args:
        file_path: Path to the file to search in.

    Returns:
        List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            comments = re.findall(r'^(TODO|FIXME|HACK):.*$', content, re.MULTILINE)
            return [Comment(tag, text) for tag, text in [comment.split(':', 1) for comment in comments]]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def replace_comments(file_path: str) -> None:
    """
    Replaces all TODO/FIXME/HACK comments in the given file with their closed versions.

    Args:
        file_path: Path to the file to modify.
    """
    comments = find_comments(file_path)
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        for comment in comments:
            start = content.find(comment.text)
            end = start + len(comment.text)
            content = content[:start] + f"{comment.tag}: {comment.text} # DONE" + content[end:]
        with open(file_path, 'w') as file:
            file.write(content)
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    """
    Replaces all TODO/FIXME/HACK comments in the file run_coder_orchestrator.py.
    """
    target_path = "tools/run_coder_orchestrator.py"
    replace_comments(target_path)

if __name__ == '__main__':
    main()
    __all__ = ['main']