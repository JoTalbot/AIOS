"""
aios_delete_lines_manually_121427.py

This module demonstrates how to replace a manual TODO/FIXME/HACK scanning
implementation with a dedicated `scan_todos` function from the
`aios_core.todo_scanner` package.

The original manual scanning logic (lines 147‑158) has been removed.
Instead, the module now imports `scan_todos`, invokes it, and exposes
the resulting list of TODO items.

The module is self‑contained, includes type hints, docstrings, and
a simple test harness under ``if __name__ == "__main__"``.
"""

from __future__ import annotations

from typing import List, Any

# Import the external scanning function
try:
    from aios_core.todo_scanner import scan_todos
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "Failed to import `scan_todos` from `aios_core.todo_scanner`. "
        "Ensure the package is installed and available."
    ) from exc

__all__ = ["get_todos", "main"]


def get_todos() -> List[Any]:
    """
    Retrieve the current list of TODO items by delegating to
    :func:`aios_core.todo_scanner.scan_todos`.

    Returns
    -------
    List[Any]
        A list of TODO items as returned by the scanner. The exact
        structure depends on the implementation of `scan_todos`.
    """
    try:
        todos = scan_todos()
    except Exception as exc:  # pragma: no cover
        # Log the error or handle it as appropriate; here we simply re‑raise
        raise RuntimeError("Error while scanning for TODO items") from exc
    return todos


def main() -> None:
    """
    Entry point for manual execution.

    Prints each TODO item retrieved by :func:`get_todos`.
    """
    todos = get_todos()
    if not todos:
        print("No TODO items found.")
        return

    print(f"Found {len(todos)} TODO item(s):")
    for idx, todo in enumerate(todos, start=1):
        print(f"{idx}. {todo}")


if __name__ == "__main__":  # pragma: no cover
    main()