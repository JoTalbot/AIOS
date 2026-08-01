#!/usr/bin/env python3
"""
tools/aios_open_run_coder_130553.py

Utility module providing a reusable function to locate code tags
such as TODO, FIXME, HACK, XXX, and BUG within Python source files.

The module is self‑contained, fully typed, and includes a minimal
unit test that can be executed directly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

__all__ = ["find_code_tags"]


def _compile_tag_regex(tags: Iterable[str]) -> re.Pattern:
    """
    Compile a regular expression that matches any of the supplied tags.

    Parameters
    ----------
    tags : Iterable[str]
        A collection of tag strings to search for.

    Returns
    -------
    re.Pattern
        A compiled regular expression object.
    """
    escaped_tags = [re.escape(tag) for tag in tags]
    pattern = r"\b(?:{})(?::|\b)".format("|".join(escaped_tags))
    return re.compile(pattern, re.IGNORECASE)


def find_code_tags(
    file_path: str | Path,
    tags: Optional[List[str]] = None,
) -> List[Tuple[int, str, str]]:
    """
    Find all occurrences of code tags in a file.

    Parameters
    ----------
    file_path : str | Path
        Path to the file to be scanned.
    tags : Optional[List[str]]
        List of tags to search for. Defaults to
        ['TODO', 'FIXME', 'HACK', 'XXX', 'BUG'].

    Returns
    -------
    List[Tuple[int, str, str]]
        A list of tuples containing the line number (1‑based),
        the matched tag, and the full line text.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    OSError
        If the file cannot be read due to permissions or other I/O errors.
    """
    if tags is None:
        tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]

    regex = _compile_tag_regex(tags)

    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    matches: List[Tuple[int, str, str]] = []

    try:
        with file_path.open(encoding="utf-8") as fp:
            for line_number, line in enumerate(fp, start=1):
                for match in regex.finditer(line):
                    matches.append((line_number, match.group(0), line.rstrip("\n")))
    except OSError as exc:
        # Re‑raise with a more descriptive message
        raise OSError(f"Error reading file {file_path}: {exc}") from exc

    return matches


if __name__ == "__main__":
    import tempfile
    import unittest

    class TestFindCodeTags(unittest.TestCase):
        def test_find_code_tags_basic(self):
            sample = """\
def foo():
    # TODO: implement this function
    pass  # FIXME: remove this line
# HACK: temporary solution
# No tag here
# XXX: something
# BUG: known issue
"""
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".py"
            ) as tmp:
                tmp.write(sample)
                tmp_path = Path(tmp.name)

            expected = [
                (2, "TODO", "# TODO: implement this function"),
                (3, "FIXME", "pass  # FIXME: remove this line"),
                (4, "HACK", "# HACK: temporary solution"),
                (6, "XXX", "# XXX: something"),
                (7, "BUG", "# BUG: known issue"),
            ]

            result = find_code_tags(tmp_path)
            self.assertEqual(result, expected)

            # Clean up temporary file
            tmp_path.unlink()

    unittest.main()