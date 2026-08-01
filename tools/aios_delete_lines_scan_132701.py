# utils/code_scanner.py
#!/usr/bin/env python3
"""
Utility module for scanning Python files for specific tags.
"""

from __future__ import annotations

import os
from typing import List, Tuple

__all__ = ["scan_for_tags"]


def scan_for_tags(root_dir: str, tags: List[str] | None = None) -> List[Tuple[str, int, str, str]]:
    """
    Walk the directory tree starting at ``root_dir`` and scan all ``.py`` files for
    lines containing any of the supplied ``tags``.  The function returns a list of
    tuples ``(filepath, line_no, tag, line_text)`` where ``line_no`` is 1‑based.

    Parameters
    ----------
    root_dir : str
        The root directory to start scanning from.
    tags : List[str] | None, optional
        A list of tag strings to search for.  If ``None`` the default tags
        ``['TODO', 'FIXME', 'HACK', 'XXX', 'BUG']`` are used.

    Returns
    -------
    List[Tuple[str, int, str, str]]
        A list of tuples describing each found tag.
    """
    if tags is None:
        tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]

    results: List[Tuple[str, int, str, str]] = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, start=1):
                        for tag in tags:
                            if tag in line:
                                results.append((file_path, line_no, tag, line.rstrip("\n")))
                                break
            except OSError:
                # Skip files that cannot be read
                continue

    return results