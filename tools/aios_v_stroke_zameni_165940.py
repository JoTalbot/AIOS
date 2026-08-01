"""
TODO scanner module for AIOS project.
Scans Python files for TODO/FIXME/HACK/XXX/BUG comments and generates reports.
"""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = ["scan_todos", "generate_todo_report"]

@dataclass
class TodoItem:
    """Represents a single TODO item found in code."""
    file: str
    line: int
    type: str
    message: str
    code_snippet: Optional[str] = None

@dataclass
class TodoReport:
    """Structured report of TODO items."""
    summary: Dict[str, int]
    todos: List[Dict]

def scan_todos(
    project_root: Path = Path.cwd(),
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None
) -> List[TodoItem]:
    """
    Scan Python files for TODO/FIXME/HACK/XXX/BUG comments.

    Args:
        project_root: Root directory to scan (default: current directory)
        exclude_patterns: List of patterns to exclude (default: ['venv', '.git', '__pycache__'])
        include_patterns: List of patterns to include (default: ['*.py'])

    Returns:
        List of TodoItem objects found in the project

    Examples:
        >>> todos = scan_todos()
        >>> for todo in todos:
        ...     print(f"{todo.file}:{todo.line} - {todo.type}: {todo.message}")

        >>> todos = scan_todos(
        ...     project_root=Path("/path/to/project"),
        ...     exclude_patterns=["venv", ".venv", ".git"]
        ... )
    """
    if exclude_patterns is None:
        exclude_patterns = ["venv", ".venv", ".git", "__pycache__"]
    if include_patterns is None:
        include_patterns = ["*.py"]

    todo_items = []
    todo_pattern = re.compile(
        r"#\s*(TODO|FIXME|HACK|XXX|BUG)\s*(?::\s*(critical|high|medium|low))?\s*:\s*(.*)",
        re.IGNORECASE
    )

    for pattern in include_patterns:
        for py_file in project_root.rglob(pattern):
            if any(excl in str(py_file) for excl in exclude_patterns):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    match = todo_pattern.search(line)
                    if match:
                        todo_type = match.group(1).upper()
                        priority = (match.group(2) or "medium").lower()
                        message = match.group(3).strip()

                        # Get code snippet (current line)
                        code_snippet = line.strip()

                        todo_items.append(
                            TodoItem(
                                file=str(py_file.relative_to(project_root)),
                                line=line_num,
                                type=todo_type,
                                message=message,
                                code_snippet=code_snippet
                            )
                        )
            except (UnicodeDecodeError, PermissionError) as e:
                print(f"Warning: Could not read {py_file}: {e}", file=sys.stderr)

    return todo_items

def generate_todo_report(
    todos: List[TodoItem],
    output_path: Path = Path("reports/todo_report.json"),
    min_priority: str = "low"
) -> TodoReport:
    """
    Generate a structured report from TODO items.

    Args:
        todos: List of TodoItem objects
        output_path: Path to save the report (default: reports/todo_report.json)
        min_priority: Minimum priority level to include (default: 'low')

    Returns:
        TodoReport object with summary and todos

    Priority levels (from highest to lowest):
        - critical
        - high
        - medium
        - low
    """
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    min_priority_level = priority_order.get(min_priority.lower(), 3)

    # Filter todos by priority
    filtered_todos = [
        todo for todo in todos
        if priority_order.get(todo.type.lower(), 3) <= min_priority_level
    ]

    # Count by priority
    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for todo in filtered_todos:
        priority = todo.type.lower()
        if priority in priority_counts:
            priority_counts[priority] += 1

    # Count total
    total = sum(priority_counts.values())

    # Prepare report data
    report_data = {
        "summary": {
            "total": total,
            **priority_counts
        },
        "todos": [
            {
                "file": todo.file,
                "line": todo.line,
                "type": todo.type,
                "priority": todo.type.lower(),
                "message": todo.message,
                "code_snippet": todo.code_snippet
            }
            for todo in filtered_todos
        ]
    }

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    return TodoReport(
        summary=report_data["summary"],
        todos=report_data["todos"]
    )

def main():
    """CLI entry point for scanning TODOs."""
    import argparse

    parser = argparse.ArgumentParser(description="Scan Python files for TODO comments")
    parser.add_argument(
        "--scan-todos",
        action="store_true",
        help="Scan for TODO/FIXME/HACK/XXX/BUG comments"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/todo_report.json",
        help="Output report file path"
    )
    parser.add_argument(
        "--min-priority",
        type=str,
        choices=["critical", "high", "medium", "low"],
        default="low",
        help="Minimum priority level to include"
    )

    args = parser.parse_args()

    if args.scan_todos:
        print("Scanning for TODO items...")
        todos = scan_todos()
        report = generate_todo_report(
            todos=todos,
            output_path=Path(args.output),
            min_priority=args.min_priority
        )
        print(f"Found {report.summary['total']} TODO items")
        print(f"Report saved to {args.output}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()