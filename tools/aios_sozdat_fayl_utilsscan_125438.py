# utils/scan_tags.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["scan_for_tags"]


def scan_for_tags(root_path: str, tags: Iterable[str]) -> List[Tuple[str, int, str]]:
    """
    Recursively search Python files under ``root_path`` for the specified ``tags``.

    Parameters
    ----------
    root_path : str
        The directory to start the search from.
    tags : Iterable[str]
        Iterable of tag strings to look for in the source files.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples containing the file path, line number (1‑based),
        and the line content where a tag was found.

    Notes
    -----
    The function performs a simple substring search; it does not parse the
    Python syntax.  It is therefore case‑sensitive and will match tags
    appearing inside string literals or comments.
    """
    root = Path(root_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Provided root_path '{root_path}' is not a directory")

    tags_set = set(tags)
    results: List[Tuple[str, int, str]] = []

    for file_path in root.rglob("*.py"):
        try:
            with file_path.open(encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if any(tag in line for tag in tags_set):
                        results.append((str(file_path), line_no, line.rstrip("\n")))
        except (OSError, UnicodeDecodeError):
            # Skip files that cannot be read
            continue

    return results