# scan_tags.py
"""
Utility module for scanning Python source files for common issue tags.

The :func:`scan_for_tags` function walks a directory tree, reads each
``.py`` file, and returns a list of tuples containing the file path,
the tag found, and the line number where the tag occurs.

Supported tags are: ``TODO``, ``FIXME``, ``HACK``, ``XXX``, and ``BUG``.
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple

__all__ = ["scan_for_tags"]


def scan_for_tags(root_path: str) -> List[Tuple[str, str, int]]:
    """
    Walk the directory tree starting at *root_path*, read each ``.py`` file,
    and return a list of tuples ``(file_path, tag, line_number)`` for every
    occurrence of the tags ``TODO``, ``FIXME``, ``HACK``, ``XXX``, or ``BUG``.

    Parameters
    ----------
    root_path : str
        The root directory to start scanning from.

    Returns
    -------
    List[Tuple[str, str, int]]
        A list of tuples containing the file path, the tag found, and the
        line number (1-indexed) where the tag occurs.
    """
    tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    tag_pattern = re.compile(r"\b(?:%s)\b" % "|".join(tags))
    results: List[Tuple[str, str, int]] = []

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, start=1):
                        for match in tag_pattern.finditer(line):
                            results.append((file_path, match.group(0), lineno))
            except OSError:
                # Skip files that cannot be read
                continue

    return results


if __name__ == "__main__":
    import pprint

    cwd = os.getcwd()
    tags_found = scan_for_tags(cwd)
    print(f"Found {len(tags_found)} tag(s) in {cwd}")
    pprint.pprint(tags_found)