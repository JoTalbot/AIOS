# tag_scanner.py
"""
Utility module for scanning files for specified tags.

This module provides a single function `scan_tags` that reads a file line by line
and returns all occurrences of any of the supplied tags.  It is intentionally
simple and robust, handling file‑reading errors gracefully.
"""

from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["scan_tags"]


def scan_tags(file_path: Path, tags: Iterable[str]) -> List[Tuple[Path, int, str]]:
    """
    Scan a file for lines containing any of the specified tags.

    Parameters
    ----------
    file_path : Path
        Path to the file to be scanned.
    tags : Iterable[str]
        Iterable of tag strings to search for.

    Returns
    -------
    List[Tuple[Path, int, str]]
        A list of tuples, each containing the file path, the line number
        (1‑indexed), and the line content where a tag was found.
    """
    results: List[Tuple[Path, int, str]] = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                if any(tag in line for tag in tags):
                    results.append((file_path, lineno, line.rstrip("\n")))
    except (OSError, UnicodeDecodeError):
        # Ignore unreadable files; the caller can decide how to handle this.
        pass
    return results