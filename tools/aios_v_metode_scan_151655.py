import ast
import os
from dataclasses import dataclass
from typing import List, Tuple

__all__ = ['scan_for_todo_fixme_hack']

@dataclass
class TodoFixmeHack:
    """Dataclass to hold TODO/FIXME/HACK information."""
    filename: str
    line_number: int
    node: ast.AST
    text: str

def scan_for_todo_fixme_hack(target_path: str) -> List[TodoFixmeHack]:
    """
    Scan the code for TODO/FIXME/HACK comments in Python files.

    Args:
    target_path: Path to the directory to scan.

    Returns:
    List of TodoFixmeHack instances.
    """
    todo_fixme_hack_list = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                                if node.value.s.startswith(('TODO', 'FIXME', 'HACK')):
                                    todo_fixme_hack_list.append(TodoFixmeHack(
                                        filename=os.path.join(root, file),
                                        line_number=node.lineno,
                                        node=node,
                                        text=node.value.s
                                    ))
                except Exception as e:
                    print(f"Error scanning {file}: {e}")
    return todo_fixme_hack_list

def test_scan_for_todo_fixme_hack():
    """Test the scan_for_todo_fixme_hack function."""
    target_path = 'tests'
    todo_fixme_hack_list = scan_for_todo_fixme_hack(target_path)
    assert len(todo_fixme_hack_list) > 0, "No TODO/FIXME/HACK comments found"

if __name__ == '__main__':
    test_scan_for_todo_fixme_hack()
    todo_fixme_hack_list = scan_for_todo_fixme_hack('.')
    for todo_fixme_hack in todo_fixme_hack_list:
        print(f"File: {todo_fixme_hack.filename}, Line: {todo_fixme_hack.line_number}, Text: {todo_fixme_hack.text}")