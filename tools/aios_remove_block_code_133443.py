"""
tools/aios_remove_block_code_133443.py

This module provides a single public function, :func:`scan_todo_tags`, which
delegates the detection of TODO/FIXME/HACK tags to the external
``lint_plugin`` helper.  The original inline scanning logic has been
removed in favour of a dedicated lint‑plugin that can be run as part of
the CI pipeline (e.g. via pre‑commit or a dedicated CI job).

The lint‑plugin is expected to raise an exception if any of the
disallowed tags are found.  ``scan_todo_tags`` simply forwards that
behaviour and provides a clear error message for the caller.
"""

from __future__ import annotations

from typing import NoReturn

# Import the lint‑plugin helper.  The plugin should be installed in the
# environment where this module is executed (e.g. via pip or a
# pre‑commit hook).
from lint_plugin import check_todo_tags

__all__ = ["scan_todo_tags"]


def scan_todo_tags() -> NoReturn:
    """
    Run the external lint‑plugin to check for TODO/FIXME/HACK tags.

    The original inline scanning logic has been removed.  The lint‑plugin
    is now responsible for detecting these tags and raising an exception
    if any are found.  This function simply forwards the call and
    propagates any exception with a clear message.

    Raises
    ------
    RuntimeError
        If the lint‑plugin detects any TODO/FIXME/HACK tags.
    """
    try:
        check_todo_tags()
    except Exception as exc:  # pragma: no cover
        # Re‑raise with a more descriptive message for CI logs.
        raise RuntimeError(
            "Lint check failed: TODO/FIXME/HACK tags were found."
        ) from exc


if __name__ == "__main__":  # pragma: no cover
    """
    Simple test harness for manual execution.

    In a CI environment this function would be invoked automatically
    by the lint‑plugin configuration (e.g. pre‑commit or a dedicated
    CI job).  Running this module directly will execute the lint
    check and print a success or failure message.
    """
    try:
        scan_todo_tags()
    except RuntimeError as err:
        print(f"❌ {err}")
        raise
    else:
        print("✅ No TODO/FIXME/HACK tags found.")