import os
import re
import ast
from dataclasses import dataclass
from typing import List

__all__ = ['check_code']

@dataclass
class Problem:
    """Dataclass to represent a problem in the code."""
    type: str
    message: str
    file: str
    line: int

def check_code(target_path: str) -> List[Problem]:
    """
    Scan Python files in the target path and identify problems.

    Args:
    target_path (str): Path to scan for Python files.

    Returns:
    List[Problem]: List of problems found in the code.
    """
    problems = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        tree = ast.parse(f.read())
                        check_for_tests(tree, file, problems)
                        check_for_errors(tree, file, problems)
                        check_for_exceptions(tree, file, problems)
                except SyntaxError as e:
                    # If there's a syntax error, add it to the problems list
                    problems.append(Problem('SyntaxError', str(e), file, e.lineno))
                except Exception as e:
                    # If any other exception occurs, add it to the problems list
                    problems.append(Problem('UnknownError', str(e), file, 0))
    return problems

def check_for_tests(tree: ast.AST, file: str, problems: List[Problem]) -> None:
    """
    Check if the code has any test functions.

    Args:
    tree (ast.AST): Abstract syntax tree of the code.
    file (str): Name of the file being checked.
    problems (List[Problem]): List of problems found in the code.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test'):
            break
    else:
        problems.append(Problem('NoTests', f"No test functions found in {file}", file, 0))

def check_for_errors(tree: ast.AST, file: str, problems: List[Problem]) -> None:
    """
    Check if the code has any error handling.

    Args:
    tree (ast.AST): Abstract syntax tree of the code.
    file (str): Name of the file being checked.
    problems (List[Problem]): List of problems found in the code.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            break
    else:
        problems.append(Problem('NoErrorHandling', f"No error handling found in {file}", file, 0))

def check_for_exceptions(tree: ast.AST, file: str, problems: List[Problem]) -> None:
    """
    Check if the code has any exception handling.

    Args:
    tree (ast.AST): Abstract syntax tree of the code.
    file (str): Name of the file being checked.
    problems (List[Problem]): List of problems found in the code.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if isinstance(handler, ast.ExceptHandler) and handler.type.id == 'Exception':
                    break
            else:
                problems.append(Problem('NoExceptionHandling', f"No exception handling found in {file}", file, 0))

if __name__ == '__main__':
    target_path = 'tools'
    problems = check_code(target_path)
    for problem in problems:
        print(f"{problem.type}: {problem.message} in {problem.file} at line {problem.line}")