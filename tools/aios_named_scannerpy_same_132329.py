# scanner.py
"""
Utility module for scanning files for specific tags.

This module provides a single public function :func:`scan_file_for_tags`
which reads a file line‑by‑line and returns a list of tuples containing
the line number and the matched tag for each occurrence of any tag in
the provided list.  The function is safe for Unicode text files,
ignores binary files, and gracefully handles I/O errors by returning
an empty list.

Author: AIOS MetaCognitiveCoder
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["scan_file_for_tags"]


def scan_file_for_tags(file_path: str | Path, tags: Iterable[str]) -> List[Tuple[int, str]]:
    """
    Scan a text file for occurrences of any of the specified tags.

    Parameters
    ----------
    file_path : str | Path
        Path to the file to be scanned.
    tags : Iterable[str]
        Iterable of tag strings to search for.

    Returns
    -------
    List[Tuple[int, str]]
        A list of tuples where each tuple contains the line number
        (1‑based) and the matched tag string.  If the file cannot be
        read as UTF‑8 text or an I/O error occurs, an empty list is
        returned.

    Notes
    -----
    * The function attempts to open the file with UTF‑8 encoding.
      If a :class:`UnicodeDecodeError` is raised, the file is
      considered binary and an empty list is returned.
    * Each tag is searched for using a simple substring match.
      If a tag appears multiple times on the same line, each
      occurrence is reported separately.
    """
    results: List[Tuple[int, str]] = []

    try:
        # Ensure we work with a Path object for consistency
        path = Path(file_path)

        # Read the file line by line with UTF‑8 decoding.
        with path.open(encoding="utf-8", errors="strict") as fp:
            for line_no, line in enumerate(fp, start=1):
                for tag in tags:
                    # Find all non‑overlapping occurrences of the tag.
                    for match in re.finditer(re.escape(tag), line):
                        results.append((line_no, tag))
    except (OSError, UnicodeDecodeError):
        # Any I/O or decoding error results in an empty list.
        return []

    return results


if __name__ == "__main__":
    # Simple self‑test when the module is executed directly.
    import tempfile
    import textwrap

    sample_text = textwrap.dedent(
        """\
        # TODO: Refactor this function
        def foo():
            pass  # FIXME: remove this
        # HACK: temporary solution
        """
    )

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".py") as tmp:
        tmp.write(sample_text)
        tmp_path = tmp.name

    tags_to_find = ["TODO", "FIXME", "HACK"]
    found = scan_file_for_tags(tmp_path, tags_to_find)
    print("Found tags:")
    for line_no, tag in found:
        print(f"  Line {line_no}: {tag}")

    # Clean up the temporary file
    Path(tmp_path).unlink()