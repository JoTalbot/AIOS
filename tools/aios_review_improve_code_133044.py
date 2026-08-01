#!/usr/bin/env python3
"""
aios_review_improve_code_133044.py

A lightweight code‑review helper that adds missing type hints and docstrings
to Python functions.  It parses the source file, injects ``Any`` type hints
for arguments and return values where they are missing, and inserts a
placeholder docstring if none exists.

The module is self‑contained, uses only the standard library, and
provides a small command‑line interface for quick testing.

Author: AIOS MetaCognitiveCoder
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, List

__all__ = ["improve_code"]


class _CodeImprover(ast.NodeTransformer):
    """
    AST transformer that adds ``Any`` type hints and placeholder docstrings
    to function definitions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.any_imported: bool = False

    def visit_Module(self, node: ast.Module) -> ast.Module:
        # Detect if ``Any`` is already imported from typing
        for stmt in node.body:
            if isinstance(stmt, ast.ImportFrom) and stmt.module == "typing":
                for alias in stmt.names:
                    if alias.name == "Any":
                        self.any_imported = True
                        break
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Add ``Any`` annotations to arguments
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.annotation is None:
                arg.annotation = ast.Name(id="Any", ctx=ast.Load())
        if node.args.vararg and node.args.vararg.annotation is None:
            node.args.vararg.annotation = ast.Name(id="Any", ctx=ast.Load())
        if node.args.kwarg and node.args.kwarg.annotation is None:
            node.args.kwarg.annotation = ast.Name(id="Any", ctx=ast.Load())

        # Add ``Any`` return annotation if missing
        if node.returns is None:
            node.returns = ast.Name(id="Any", ctx=ast.Load())

        # Insert placeholder docstring if missing
        if ast.get_docstring(node) is None:
            docstring = ast.Expr(
                value=ast.Constant(value=f"{node.name} function.")
            )
            node.body.insert(0, docstring)

        return node


def improve_code(file_path: str) -> str:
    """
    Read a Python source file, add missing type hints and docstrings,
    and return the improved source code as a string.

    Parameters
    ----------
    file_path : str
        Path to the Python file to be improved.

    Returns
    -------
    str
        The transformed source code.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    SyntaxError
        If the source code cannot be parsed.
    """
    source = Path(file_path).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        raise SyntaxError(f"Failed to parse {file_path!r}: {exc}") from exc

    transformer = _CodeImprover()
    transformer.visit(tree)

    # Ensure ``Any`` is imported if we added annotations
    if not transformer.any_imported:
        import_stmt = ast.ImportFrom(
            module="typing",
            names=[ast.alias(name="Any", asname=None)],
            level=0,
        )
        tree.body.insert(0, import_stmt)

    # Convert the AST back to source code
    try:
        improved_source = ast.unparse(tree)
    except Exception as exc:
        raise RuntimeError("Failed to unparse the modified AST") from exc

    return improved_source


def _demo() -> None:
    """
    Demonstrate the code improvement on a temporary file.
    """
    sample_code = """
def greet(name):
    print(f"Hello, {name}!")

def add(a, b):
    return a + b
"""
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(sample_code)
        tmp_path = tmp.name

    try:
        improved = improve_code(tmp_path)
        print("=== Improved Code ===")
        print(improved)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python aios_review_improve_code_133044.py <path-to-file>")
        print("Running demo...")
        _demo()
    else:
        target = sys.argv[1]
        try:
            result = improve_code(target)
            print(result)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)