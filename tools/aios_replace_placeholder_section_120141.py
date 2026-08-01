# tools/aios_replace_placeholder_section_120141.py
"""
Utility module for scanning Python source files for common issue tags
such as TODO, FIXME, HACK, XXX, and BUG.

The :func:`scan_for_tags` function walks through all ``.py`` files in a
given directory, extracts tag occurrences, writes a JSON report to the
project root, and returns the collected data as a list of dictionaries.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

__all__ = ["scan_for_tags", "main"]


@dataclass
class TagOccurrence:
    """Represents a single tag occurrence in a source file."""
    file_path: str
    line_number: int
    tag: str
    line_text: str


def _find_tags_in_line(line: str) -> List[TagOccurrence]:
    """
    Search a single line for any of the target tags.

    Parameters
    ----------
    line : str
        The line of text to search.

    Returns
    -------
    List[TagOccurrence]
        A list of :class:`TagOccurrence` objects found in the line.
    """
    tags = []
    for match in re.finditer(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", line):
        tags.append(TagOccurrence("", 0, match.group(0), line.rstrip("\n")))
    return tags


def scan_for_tags(root_dir: str) -> List[Dict[str, Any]]:
    """
    Walk through all ``.py`` files under *root_dir*, collect occurrences of
    the tags ``TODO``, ``FIXME``, ``HACK``, ``XXX``, and ``BUG``.

    For each occurrence a dictionary with the following keys is recorded:
    ``file_path`` (relative to *root_dir*), ``line_number``, ``tag``, and
    ``line_text`` (the full line content).

    The collected data is written to ``todo_report.json`` in *root_dir*.

    Parameters
    ----------
    root_dir : str
        The directory to start scanning from.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries describing each tag occurrence.
    """
    occurrences: List[TagOccurrence] = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as fp:
                    for line_number, line in enumerate(fp, start=1):
                        for tag_occurrence in _find_tags_in_line(line):
                            tag_occurrence.file_path = os.path.relpath(
                                file_path, root_dir
                            )
                            tag_occurrence.line_number = line_number
                            occurrences.append(tag_occurrence)
            except (OSError, UnicodeDecodeError) as exc:
                print(
                    f"Warning: could not read {file_path!r}: {exc}",
                    file=sys.stderr,
                )

    # Convert dataclass instances to dictionaries
    result: List[Dict[str, Any]] = [asdict(occ) for occ in occurrences]

    # Write JSON report
    report_path = os.path.join(root_dir, "todo_report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"Error writing report to {report_path!r}: {exc}", file=sys.stderr)

    return result


def main() -> None:
    """
    Entry point for the module when executed as a script.

    Scans the current working directory for tags and prints a summary
    of the total number of tags found.
    """
    cwd = os.getcwd()
    tags = scan_for_tags(cwd)
    print(f"Found {len(tags)} tag(s) in {cwd}")


if __name__ == "__main__":
    main()