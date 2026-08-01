"""
aios_helper_inside_run_124427.py

Utility module providing a helper function to scan Python source files for
specific tags such as TODO, FIXME, HACK, XXX, and BUG. The function walks
through a directory tree, reads each `.py` file, and returns a list of
tuples containing the file path, line number, and the line text that
contains any of the specified tags.

The module is self‑contained, includes type hints, a comprehensive
docstring, and a small test harness that can be executed directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["scan_for_tags"]


def scan_for_tags(path: str, tags: Iterable[str]) -> List[Tuple[str, int, str]]:
    """
    Recursively scan a directory for Python files and collect lines that
    contain any of the specified tags.

    Parameters
    ----------
    path : str
        The root directory to start scanning from.
    tags : Iterable[str]
        An iterable of tag strings to look for (e.g. ``["TODO", "FIXME"]``).

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples where each tuple contains:
        - The absolute file path as a string.
        - The 1‑based line number where the tag was found.
        - The line text (without the trailing newline).

    Notes
    -----
    * Only files ending with ``.py`` are inspected.
    * Files that cannot be opened or decoded as UTF‑8 are silently skipped.
    * Binary files are skipped by attempting to open them in text mode;
      a ``UnicodeDecodeError`` indicates a binary file and causes the file
      to be ignored.
    """
    results: List[Tuple[str, int, str]] = []
    tags_set = set(tags)

    for root, _dirs, files in os.walk(path):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            file_path = Path(root) / filename
            try:
                with file_path.open(encoding="utf-8") as f:
                    for lineno, line in enumerate(f, start=1):
                        if any(tag in line for tag in tags_set):
                            results.append((str(file_path), lineno, line.rstrip("\n")))
            except (UnicodeDecodeError, OSError):
                # Skip binary files or files that cannot be read.
                continue

    return results


if __name__ == "__main__":
    # Simple test harness: scan the current working directory for common tags.
    import pprint

    tags_to_find = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    found = scan_for_tags(os.getcwd(), tags_to_find)

    if found:
        print(f"Found {len(found)} tag(s) in the current directory:")
        for file_path, line_no, line_text in found:
            print(f"{file_path}:{line_no} -> {line_text}")
    else:
        print("No tags found.")