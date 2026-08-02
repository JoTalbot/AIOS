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

def clean_todos(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Remove all TODO items from context if they are empty or not actionable.

    Args:
        ctx: The execution context dictionary containing todos

    Returns:
        Updated context with cleaned todos

    Raises:
        TypeError: If ctx is not a dictionary

    This function removes all TODO items that are:
    - Empty strings
    - None values
    - Whitespace-only strings
    - Strings shorter than 5 characters (likely not meaningful)
    """
    if not isinstance(ctx, dict):
        raise TypeError("Context must be a dictionary")

    if "todos" not in ctx:
        return ctx

    cleaned = [
        todo for todo in ctx["todos"]
        if todo and str(todo).strip() and len(str(todo).strip()) >= 5
    ]
    ctx["todos"] = cleaned
    return ctx

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