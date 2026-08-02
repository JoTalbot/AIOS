"""Context Window Auto-Pacer for AIOS v11.94.0."""

from __future__ import annotations

import time
from typing import Any, Dict, List

def safe_filter_todos(ctx: Dict[str, Any], last_file: str) -> Dict[str, Any]:
    """Safely filter TODO items from context by file path.

    Removes all TODO items that contain the specified file path to prevent
    execution of stale tasks or potential data leaks from previous contexts.

    Args:
        ctx: Execution context dictionary potentially containing 'todos' key
        last_file: File path to filter TODOs against (case-sensitive)

    Returns:
        New context dictionary with filtered TODOs (original ctx is not modified)

    Raises:
        TypeError: If ctx is not a dictionary or last_file is not a string
    """
    if not isinstance(ctx, dict):
        raise TypeError("Context must be a dictionary")
    if not isinstance(last_file, str):
        raise TypeError("last_file must be a string")

    if "todos" not in ctx:
        return ctx.copy()

    filtered_todos = [
        todo for todo in ctx["todos"]
        if not isinstance(todo, str) or last_file not in todo
    ]

    new_ctx = ctx.copy()
    new_ctx["todos"] = filtered_todos
    return new_ctx


class ContextWindowAutoPacer:
    """Paces context window sizes."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def pace_context(self, tokens: int) -> Dict[str, Any]:
        """
        Paces the context window size.

        Args:
            tokens: The requested number of tokens.

        Returns:
            A dictionary containing the requested tokens, paced tokens, and timestamp.
        """
        result: Dict[str, Any] = {
            "requested_tokens": tokens,
            "paced_tokens": min(tokens, 8192),
            "timestamp": time.time(),
        }
        self.history.append(result)
        return result