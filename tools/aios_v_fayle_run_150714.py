import os
import re
import ast
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    file_path: str
    lines_of_code: int
    complexity: int
    errors: List[str]

class CodeAnalyzer:
    """Class for code analysis."""
    def __init__(self, target_path: str):
        self.target_path = target_path

    def analyze(self) -> CodeAnalysisResult:
        """Analyze code in the target file."""
        try:
            with open(self.target_path, 'r') as file:
                code = file.read()
                tree = ast.parse(code)
                lines_of_code = len(re.findall(r'\n', code))
                complexity = self.calculate_complexity(tree)
                errors = self.find_errors(tree)
                return CodeAnalysisResult(self.target_path, lines_of_code, complexity, errors)
        except FileNotFoundError:
            print(f"File {self.target_path} not found.")
            return None
        except Exception as e:
            print(f"Error analyzing code: {e}")
            return None

    def calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate code complexity."""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                complexity += 1
            elif isinstance(node, ast.For):
                complexity += 1
            elif isinstance(node, ast.While):
                complexity += 1
        return complexity

    def find_errors(self, tree: ast.AST) -> List[str]:
        """Find errors in the code."""
        errors = []
        for node in ast.walk(tree):
            if isinstance(node, ast.NameError):
                errors.append(f"NameError: {node.id}")
        return errors

class Scanner:
    """Class for code scanning."""
    def __init__(self, target_path: str):
        self.target_path = target_path

    def scan(self) -> Dict[str, int]:
        """Scan code in the target file."""
        try:
            with open(self.target_path, 'r') as file:
                code = file.read()
                lines_of_code = len(re.findall(r'\n', code))
                return {"lines_of_code": lines_of_code}
        except FileNotFoundError:
            print(f"File {self.target_path} not found.")
            return None
        except Exception as e:
            print(f"Error scanning code: {e}")
            return None

def main():
    """Main function."""
    target_path = "tools/aios_v_fayle_run_150714.py"
    analyzer = CodeAnalyzer(target_path)
    scanner = Scanner(target_path)
    result = analyzer.analyze()
    if result:
        print(f"File: {result.file_path}")
        print(f"Lines of code: {result.lines_of_code}")
        print(f"Complexity: {result.complexity}")
        print(f"Errors: {result.errors}")
    scan_result = scanner.scan()
    if scan_result:
        print(f"Lines of code: {scan_result['lines_of_code']}")

if __name__ == '__main__':
    main()