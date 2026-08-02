# aios_core/context_processor.py
from typing import Any, Dict, List, Optional

def filter_todos_by_file(ctx: Dict[str, Any], excluded_file: str) -> Dict[str, Any]:
    """Filter out TODO items containing the specified file path from context.

    Args:
        ctx: The execution context dictionary containing todos
        excluded_file: File path to filter TODOs against (todos containing this path will be removed)

    Returns:
        Updated context with filtered todos

    Raises:
        ValueError: If excluded_file is None or empty string
        TypeError: If ctx is not a dictionary or excluded_file is not a string

    This function removes all TODO items that contain the specified file path in their content,
    preventing stale TODOs from affecting new task execution. The filtering is case-sensitive.
    """
    if not isinstance(ctx, dict):
        raise TypeError("Context must be a dictionary")
    if not excluded_file or not isinstance(excluded_file, str):
        raise ValueError("excluded_file must be a non-empty string")

    if "todos" not in ctx:
        return ctx

    ctx["todos"] = [todo for todo in ctx["todos"] if excluded_file not in str(todo)]
    return ctx

def cleanup_todos_context(ctx: Dict[str, Any], last_file: str = None) -> None:
    """Clean up TODO items by removing those related to the specified file.

    Args:
        ctx: The execution context dictionary containing todos
        last_file: File path to filter TODOs against (todos containing this path will be removed)

    Returns:
        None: Modifies ctx in-place

    This function removes all TODO items that contain the specified file path in their content,
    preventing stale TODOs from affecting new task execution. If last_file is None, clears all todos.
    """
    if not isinstance(ctx, dict):
        raise TypeError("Context must be a dictionary")

    if "todos" not in ctx:
        return

    if last_file:
        ctx["todos"] = [todo for todo in ctx["todos"] if last_file not in str(todo)]
    else:
        ctx["todos"] = []

def validate_context(ctx: Optional[Dict[str, Any]]) -> bool:
    """Validate the context dictionary structure.

    Args:
        ctx: The context dictionary to validate

    Returns:
        bool: True if context is valid, False otherwise
    """
    if ctx is None:
        return False
    if not isinstance(ctx, dict):
        return False
    return True