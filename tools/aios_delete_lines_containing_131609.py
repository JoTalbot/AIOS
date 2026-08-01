# utils/todo_scanner.py
"""
Utility module for scanning TODO-like tags in Python files.
"""

from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_todos"]


def scan_todos(root_path: str) -> List[Tuple[str, int, str]]:
    """
    Walk through all .py files under `root_path`, collect TODO-like tags.

    Parameters
    ----------
    root_path : str
        The root directory to start scanning.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples containing (file_path, line_number, tag).
    """
    tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    todos: List[Tuple[str, int, str]] = []

    root = Path(root_path)
    if not root.is_dir():
        return todos

    for file_path in root.rglob("*.py"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                for idx, line in enumerate(f, start=1):
                    for tag in tags:
                        if tag in line:
                            todos.append((str(file_path), idx, tag))
                            break
        except (OSError, UnicodeDecodeError):
            # Skip files that cannot be read
            continue

    return todos