"""
aios_core.todo_scanner

Utility module for scanning Python source files for TODO-like tags.

The :func:`scan_todos` function walks a directory tree and collects
lines that contain any of the default or user‑supplied tags.
"""

from __future__ import annotations

import os
from typing import List, Tuple

__all__ = ["scan_todos"]


def scan_todos(
    root_dir: str,
    tags: List[str] | None = None,
) -> List[Tuple[str, int, str]]:
    """
    Recursively scan Python files under *root_dir* for lines containing any of *tags*.

    Parameters
    ----------
    root_dir : str
        The directory to start scanning from.
    tags : list[str] | None, optional
        Tags to look for. If ``None`` the default tags
        ``["TODO", "FIXME", "HACK", "XXX", "BUG"]`` are used.

    Returns
    -------
    list[tuple[str, int, str]]
        A list of tuples ``(file_path, line_no, line_text)`` for each
        matching line found.

    Notes
    -----
    Files that cannot be opened or decoded are silently skipped.
    """
    if tags is None:
        tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]

    todos: List[Tuple[str, int, str]] = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            file_path = os.path.join(dirpath, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        if any(tag in line for tag in tags):
                            todos.append((file_path, line_no, line.rstrip()))
            except (OSError, UnicodeDecodeError):
                # Skip files that cannot be read
                continue

    return todos


if __name__ == "__main__":
    import shutil
    import tempfile

    # Create a temporary directory with a sample Python file
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = os.path.join(tmp_dir, "sample.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                """# Sample file
def foo():
    pass  # TODO: implement
# FIXME: this is broken
# No tag here
"""
            )

        # Scan the temporary directory
        results = scan_todos(tmp_dir)

        # Print the results
        print("Found TODO-like entries:")
        for file_path, line_no, line_text in results:
            print(f"{file_path}:{line_no} -> {line_text}")

        # Clean up is handled automatically by TemporaryDirectory