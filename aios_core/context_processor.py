# aios_core/context_processor.py
from typing import Any, Dict, List
from aios_core.code_refactorer import TodoItem

def filter_todos_by_file(ctx: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Filter out TODO items containing the specified file path from context.

    This is a unified TODO filtering method that replaces duplicate filtering
    logic that previously existed in multiple places. It ensures consistent
    behavior across the codebase and prevents potential conflicts from
    multiple filtering passes.

    Args:
        ctx: The execution context dictionary that may contain todos
        file_path: File path to filter TODOs against

    Returns:
        Updated context with filtered todos

    Example:
        >>> ctx = {"todos": ["TODO: fix file.py", "TODO: refactor utils.py"]}
        >>> filter_todos_by_file(ctx, "file.py")
        {"todos": ["TODO: refactor utils.py"]}
    """
    if "todos" in ctx:
        # Remove all todos that contain the specified file path
        ctx["todos"] = [todo for todo in ctx.get("todos", [])
                       if file_path not in str(todo)]
    return ctx

def filter_todos_by_todo_items(ctx: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Filter TODO items by file path using TodoItem objects.

    Alternative filtering method that works with structured TodoItem objects.
    This provides more precise filtering when working with TodoItem instances.

    Args:
        ctx: The execution context dictionary that may contain todos as TodoItem objects
        file_path: File path to filter by

    Returns:
        Updated context with filtered todos
    """
    if "todos" in ctx:
        todos = ctx["todos"]
        if todos and isinstance(todos[0], TodoItem):
            # Filter TodoItem objects by file path
            ctx["todos"] = [todo for todo in todos if todo.file_path != file_path]
    return ctx

def clean_context_todos(ctx: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Clean TODO items from context for the specified file.

    Unified method that handles both string-based and TodoItem-based todos.
    This is the recommended method to use for all TODO filtering operations.

    Args:
        ctx: The execution context dictionary
        file_path: File path to clean TODOs for

    Returns:
        Updated context with cleaned todos

    Note:
        This method replaces the duplicate filtering logic that previously
        existed in multiple places in the codebase. It ensures consistent
        behavior and prevents potential conflicts from multiple filtering passes.
    """
    # First try to filter as TodoItem objects if they exist
    ctx = filter_todos_by_todo_items(ctx, file_path)

    # Then filter string-based todos as fallback
    ctx = filter_todos_by_file(ctx, file_path)

    return ctx