from dataclasses import dataclass
from pathlib import Path
import re
import ast

__all__ = ['analyze_code']

@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    lines_of_code: int
    comments: int
    functions: int
    classes: int

def _count_lines_of_code(code: str) -> int:
    """Count lines of code in the given string."""
    return len(code.splitlines())

def _count_comments(code: str) -> int:
    """Count comments in the given string."""
    return len(re.findall(r'#.*|"""[^"]*"""|\'\'\'.*?\'\'\'', code))

def _count_functions(code: str) -> int:
    """Count functions in the given string."""
    tree = ast.parse(code)
    return len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])

def _count_classes(code: str) -> int:
    """Count classes in the given string."""
    tree = ast.parse(code)
    return len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])

def analyze_code(target_path: Path) -> CodeAnalysisResult:
    """Analyze code at the given target path."""
    try:
        with target_path.open('r') as file:
            code = file.read()
            lines_of_code = _count_lines_of_code(code)
            comments = _count_comments(code)
            functions = _count_functions(code)
            classes = _count_classes(code)
            return CodeAnalysisResult(lines_of_code, comments, functions, classes)
    except FileNotFoundError:
        print(f"File not found: {target_path}")
        return CodeAnalysisResult(0, 0, 0, 0)
    except Exception as e:
        print(f"Error analyzing code: {e}")
        return CodeAnalysisResult(0, 0, 0, 0)

if __name__ == '__main__':
    target_path = Path('path_to_your_code_file.py')
    result = analyze_code(target_path)
    print(f"Lines of code: {result.lines_of_code}")
    print(f"Comments: {result.comments}")
    print(f"Functions: {result.functions}")
    print(f"Classes: {result.classes}")