import os
import ast
from dataclasses import dataclass
from typing import List, Tuple

__all__ = ['scan_for_todo_fixhack']

@dataclass
class TodoFixhack:
    """Dataclass to hold TODO/FIXME/HACK information."""
    file_path: str
    line_number: int
    comment: str

def scan_for_todo_fixhack(target_path: str) -> List[TodoFixhack]:
    """
    Scan the target path for TODO/FIXME/HACK comments in all files.

    Args:
    target_path: The path to scan.

    Returns:
    A list of TodoFixhack objects containing TODO/FIXME/HACK information.
    """
    todo_fixhack_list = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                            comment = node.value.s
                            if comment.startswith(('TODO', 'FIXME', 'HACK')):
                                todo_fixhack_list.append(TodoFixhack(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    comment=comment
                                ))
            except Exception as e:
                print(f"Error scanning file {file_path}: {str(e)}")
    return todo_fixhack_list

if __name__ == '__main__':
    target_path = os.path.dirname(__file__)
    todo_fixhack_list = scan_for_todo_fixhack(target_path)
    for todo_fixhack in todo_fixhack_list:
        print(f"File: {todo_fixhack.file_path}, Line: {todo_fixhack.line_number}, Comment: {todo_fixhack.comment}")