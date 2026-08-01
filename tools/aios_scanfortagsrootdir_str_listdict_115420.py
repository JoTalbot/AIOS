#!/usr/bin/env python3
"""
aios_scanfortagsrootdir_str_listdict_115420.py

This module is part of the CI pipeline. It scans all Python files in the
project root for the tags TODO, FIXME, HACK, XXX, and BUG, generates a
JSON report, and exits with a non‑zero status if any tags are found.
The script should be run before deployment to ensure code quality.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

__all__ = [
    "scan_for_tags",
    "generate_report",
    "run_report",
]

# Configure module‑level logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Regular expression to find tags in a line
_TAG_REGEX = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b(.*)")

def scan_for_tags(root_dir: str) -> List[Dict[str, str | int]]:
    """
    Walk through all .py files under ``root_dir`` and collect occurrences
    of the tags TODO, FIXME, HACK, XXX, and BUG.

    Parameters
    ----------
    root_dir : str
        The root directory to start scanning from.

    Returns
    -------
    List[Dict[str, str | int]]
        A list of dictionaries, each containing:
        - file (str): relative path to the file
        - line_number (int): line number where the tag was found
        - tag (str): the tag that was matched
        - text (str): the remaining text on the line after the tag
    """
    entries: List[Dict[str, str | int]] = []
    root_path = Path(root_dir).resolve()

    if not root_path.is_dir():
        logger.error("Provided root_dir '%s' is not a directory.", root_dir)
        return entries

    for py_file in root_path.rglob("*.py"):
        try:
            with py_file.open(encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    for match in _TAG_REGEX.finditer(line):
                        tag, text = match.group(1), match.group(2).strip()
                        entries.append(
                            {
                                "file": str(py_file.relative_to(root_path)),
                                "line_number": line_no,
                                "tag": tag,
                                "text": text,
                            }
                        )
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Could not read file '%s': %s", py_file, exc)

    return entries

def generate_report(entries: List[Dict[str, str | int]], output_path: str) -> None:
    """
    Serialize the list of entries to JSON and write it to ``output_path``.

    Parameters
    ----------
    entries : List[Dict[str, str | int]]
        The list of tag entries to serialize.
    output_path : str
        Path where the JSON report will be written.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, sort_keys=True)
        logger.info("Report written to '%s' (%d entries).", output_path, len(entries))
    except OSError as exc:
        logger.error("Failed to write report to '%s': %s", output_path, exc)

def run_report() -> None:
    """
    Main entry point for the script. Scans for tags, generates a report,
    logs the number of findings, and exits with a non‑zero status if any
    tags are found.
    """
    project_root = Path(__file__).resolve().parent.parent  # Adjust if needed
    logger.info("Scanning project root: %s", project_root)

    entries = scan_for_tags(str(project_root))
    report_path = project_root / "todo_report.json"
    generate_report(entries, str(report_path))

    if entries:
        logger.warning("Found %d tag(s). Exiting with status 1.", len(entries))
        sys.exit(1)
    logger.info("No tags found. Exiting with status 0.")
    sys.exit(0)

# --------------------------------------------------------------------------- #
# Placeholder for existing TODO/FIXME/HACK code at lines 147‑161
# --------------------------------------------------------------------------- #
# The following section used to be a no‑op placeholder. It has been updated
# to invoke the new tag scanning functionality before deployment.
# --------------------------------------------------------------------------- #

# Example placeholder (lines 147‑161):
# def placeholder_function():
#     """
#     This function previously did nothing. It now triggers the tag scan.
#     """
#     run_report()

# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # Simple test harness: run the report when executed directly.
    run_report()