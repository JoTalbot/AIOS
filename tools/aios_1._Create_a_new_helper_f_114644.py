"""
tools/aios_1._Create_a_new_helper_f_114644.py

This module provides a helper function to scan Python source files for
common issue tags such as TODO, FIXME, HACK, XXX, and BUG.  It is
intended for use in continuous‑integration pipelines to surface
potential problems before code is merged.

The module exposes a command‑line interface with the flag
``--report-issues``.  When this flag is supplied, the script will
recursively scan the current working directory for Python files,
collect any lines containing the tags, pretty‑print the results as
JSON to stdout, and then exit.

The helper function is unit‑tested in ``tests/test_issue_scanner.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

__all__ = ["scan_for_issues"]


def scan_for_issues(root_dir: str, tags: List[str]) -> List[Dict[str, str]]:
    """
    Recursively scan ``root_dir`` for Python files and collect lines
    containing any of the specified ``tags``.

    Parameters
    ----------
    root_dir : str
        The directory to start scanning from.
    tags : List[str]
        A list of tag strings to look for (e.g., ["TODO", "FIXME"]).

    Returns
    -------
    List[Dict[str, str]]
        A list of dictionaries, each representing an issue found.
        Keys are ``file`` (relative path), ``line_no`` (1‑based),
        ``tag`` (the matched tag), and ``text`` (the remainder of the
        line after the tag).

    Notes
    -----
    The function is tolerant of file‑reading errors; any file that
    cannot be read is skipped with a warning printed to stderr.
    """
    issues: List[Dict[str, str]] = []
    tag_pattern = re.compile(r"\b(" + "|".join(map(re.escape, tags)) + r")\b")

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = Path(dirpath) / filename
            try:
                with file_path.open(encoding="utf-8") as fp:
                    for line_no, line in enumerate(fp, start=1):
                        match = tag_pattern.search(line)
                        if match:
                            tag = match.group(1)
                            # Capture everything after the tag
                            text = line[match.end():].strip()
                            issues.append(
                                {
                                    "file": str(file_path.relative_to(root_dir)),
                                    "line_no": str(line_no),
                                    "tag": tag,
                                    "text": text,
                                }
                            )
            except (OSError, UnicodeDecodeError) as exc:
                print(
                    f"Warning: could not read {file_path}: {exc}",
                    file=sys.stderr,
                )
    return issues


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Python files for issue tags and report them."
    )
    parser.add_argument(
        "--report-issues",
        action="store_true",
        help="Scan for issue tags and output a JSON report.",
    )
    parser.add_argument(
        "--root-dir",
        default=os.getcwd(),
        help="Root directory to start scanning from (default: current directory).",
    )
    return parser.parse_args()


def _main() -> None:
    args = _parse_args()
    if args.report_issues:
        tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
        issues = scan_for_issues(args.root_dir, tags)
        print(json.dumps(issues, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    _main()