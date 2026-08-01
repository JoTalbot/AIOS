import os
import re
import json
from dataclasses import dataclass
from typing import Dict, List

__all__ = ['scan_python_files']

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    type: str
    text: str

@dataclass
class File:
    """Dataclass to represent a Python file."""
    path: str
    comments: List[Comment]

def scan_python_files(directory: str) -> Dict[str, List[str]]:
    """
    Scan Python files in the given directory and collect TODO/FIXME/HACK comments.

    Args:
    directory (str): Path to the directory to scan.

    Returns:
    Dict[str, List[str]]: Dictionary with keys 'todos', 'fixmes', 'hacks' and values - lists of corresponding comments.
    """
    try:
        comments: Dict[str, List[str]] = {'todos': [], 'fixmes': [], 'hacks': []}
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        todos = re.findall(r'# TODO: (.*)', content, re.MULTILINE)
                        fixmes = re.findall(r'# FIXME: (.*)', content, re.MULTILINE)
                        hacks = re.findall(r'# HACK: (.*)', content, re.MULTILINE)
                        comments['todos'].extend(todos)
                        comments['fixmes'].extend(fixmes)
                        comments['hacks'].extend(hacks)
        return comments
    except Exception as e:
        print(f"Error scanning files: {e}")
        return {}

def to_json(comments: Dict[str, List[str]]) -> str:
    """
    Convert the comments dictionary to JSON.

    Args:
    comments (Dict[str, List[str]]): Dictionary with keys 'todos', 'fixmes', 'hacks' and values - lists of corresponding comments.

    Returns:
    str: JSON string representing the comments dictionary.
    """
    return json.dumps(comments, indent=4)

def main():
    directory = 'path_to_your_directory'
    comments = scan_python_files(directory)
    print(to_json(comments))

if __name__ == '__main__':
    main()