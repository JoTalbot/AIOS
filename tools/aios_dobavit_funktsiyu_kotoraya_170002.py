"""
Module for aggregating TODO comments, code complexity metrics, and test coverage.
This module provides functionality to analyze Python codebases and generate reports
on technical debt and quality metrics.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

__all__ = [
    "CodeAnalysisResult",
    "TodoItem",
    "CodeComplexityAnalyzer",
    "TestCoverageAnalyzer",
    "aggregate_code_metrics",
]

@dataclass
class TodoItem:
    """Represents a TODO comment found in the code."""

    file_path: str
    line_number: int
    description: str
    priority: Optional[str] = None

@dataclass
class CodeAnalysisResult:
    """Container for aggregated code analysis results."""

    todos: List[TodoItem]
    complexity_metrics: Dict[str, float]
    test_coverage: float
    total_files: int
    analyzed_files: List[str]

class CodeComplexityAnalyzer:
    """
    Analyzes code complexity metrics using Abstract Syntax Tree (AST) parsing.
    Calculates cyclomatic complexity and other complexity metrics.
    """

    def __init__(self, max_line_length: int = 120, max_nesting: int = 5) -> None:
        """
        Initialize the complexity analyzer.

        Args:
            max_line_length: Maximum allowed line length (for complexity)
            max_nesting: Maximum allowed nesting level (for complexity)
        """
        self.max_line_length = max_line_length
        self.max_nesting = max_nesting

    def analyze_file(self, file_path: str | Path) -> Dict[str, float]:
        """
        Analyze a single Python file for complexity metrics.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            Dictionary containing complexity metrics
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                source = file.read()
        except (IOError, UnicodeDecodeError) as e:
            raise ValueError(f"Could not read file {file_path}: {e}")

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

        metrics = {
            "cyclomatic_complexity": self._calculate_cyclomatic_complexity(tree),
            "average_line_length": self._calculate_avg_line_length(source),
            "max_nesting_level": self._calculate_max_nesting(tree),
            "function_count": self._count_functions(tree),
            "class_count": self._count_classes(tree),
        }

        return metrics

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> float:
        """Calculate cyclomatic complexity based on AST nodes."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                complexity += 1

        return complexity

    def _calculate_avg_line_length(self, source: str) -> float:
        """Calculate average line length in characters."""
        lines = source.splitlines()
        if not lines:
            return 0.0

        total_length = sum(len(line) for line in lines)
        return total_length / len(lines)

    def _calculate_max_nesting(self, tree: ast.AST) -> int:
        """Calculate maximum nesting level in the code."""
        max_nesting = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While)):
                current_nesting = self._get_nesting_level(node)
                if current_nesting > max_nesting:
                    max_nesting = current_nesting

        return max_nesting

    def _get_nesting_level(self, node: ast.AST) -> int:
        """Get nesting level of a node by counting parent nodes."""
        level = 0
        current = node
        while hasattr(current, "parent"):
            level += 1
            current = current.parent
        return level

    def _count_functions(self, tree: ast.AST) -> int:
        """Count the number of function definitions."""
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))

    def _count_classes(self, tree: ast.AST) -> int:
        """Count the number of class definitions."""
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

class TestCoverageAnalyzer:
    """
    Analyzes test coverage by looking for test files and coverage reports.
    This is a simplified version that looks for common test file patterns.
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        """
        Initialize the test coverage analyzer.

        Args:
            project_root: Root directory of the project (optional)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_coverage(self, coverage_file: str | Path | None = None) -> float:
        """
        Analyze test coverage from a coverage report file or estimate from test files.

        Args:
            coverage_file: Path to coverage report file (optional)

        Returns:
            Test coverage percentage (0-100)
        """
        if coverage_file:
            return self._parse_coverage_file(coverage_file)

        # Fallback: estimate coverage based on presence of test files
        return self._estimate_coverage_from_tests()

    def _parse_coverage_file(self, coverage_file: str | Path) -> float:
        """Parse a coverage report file to extract coverage percentage."""
        try:
            with open(coverage_file, "r", encoding="utf-8") as file:
                content = file.read()

            # Try to find coverage percentage in common formats
            patterns = [
                r"TOTAL.*?(\d+\.\d+)%",
                r"Coverage:\s*(\d+\.?\d*)%",
                r"(\d+\.?\d*)%\s*covered",
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return float(match.group(1))

            return 0.0

        except (IOError, ValueError) as e:
            raise ValueError(f"Could not parse coverage file {coverage_file}: {e}")

    def _estimate_coverage_from_tests(self) -> float:
        """Estimate coverage based on the presence of test files."""
        test_files = list(self.project_root.rglob("*test*.py"))
        total_files = len(list(self.project_root.rglob("*.py")))

        if total_files == 0:
            return 0.0

        # Simple heuristic: more test files = higher coverage
        coverage = min(95.0, len(test_files) * 5.0)
        return round(coverage, 2)

class TodoAnalyzer:
    """
    Analyzes Python files for TODO comments and extracts them with context.
    """

    def __init__(self, todo_patterns: Optional[List[str]] = None) -> None:
        """
        Initialize the TODO analyzer.

        Args:
            todo_patterns: Custom patterns for TODO detection (optional)
        """
        self.todo_patterns = todo_patterns or [
            r"#\s*TODO\s*(?:\(([^)]+)\))?\s*:?\s*(.*)",
            r"#\s*FIXME\s*(?:\(([^)]+)\))?\s*:?\s*(.*)",
            r"#\s*XXX\s*(?:\(([^)]+)\))?\s*:?\s*(.*)",
        ]

    def find_todos(self, file_path: str | Path) -> List[TodoItem]:
        """
        Find all TODO comments in a Python file.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            List of TodoItem objects
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except (IOError, UnicodeDecodeError) as e:
            raise ValueError(f"Could not read file {file_path}: {e}")

        todos = []
        for line_num, line in enumerate(lines, 1):
            for pattern in self.todo_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    priority = match.group(1) if match.group(1) else None
                    description = match.group(2).strip() if match.group(2) else ""
                    todos.append(
                        TodoItem(
                            file_path=str(file_path),
                            line_number=line_num,
                            description=description,
                            priority=priority,
                        )
                    )
                    break

        return todos

def aggregate_code_metrics(
    project_path: str | Path,
    complexity_analyzer: Optional[CodeComplexityAnalyzer] = None,
    todo_analyzer: Optional[TodoAnalyzer] = None,
    coverage_analyzer: Optional[TestCoverageAnalyzer] = None,
) -> CodeAnalysisResult:
    """
    Aggregate code metrics from a project: TODOs, complexity, and test coverage.

    Args:
        project_path: Path to the project directory
        complexity_analyzer: Optional custom complexity analyzer
        todo_analyzer: Optional custom TODO analyzer
        coverage_analyzer: Optional custom coverage analyzer

    Returns:
        CodeAnalysisResult containing aggregated metrics
    """
    project_path = Path(project_path)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_path}")

    # Initialize analyzers if not provided
    complexity_analyzer = complexity_analyzer or CodeComplexityAnalyzer()
    todo_analyzer = todo_analyzer or TodoAnalyzer()
    coverage_analyzer = coverage_analyzer or TestCoverageAnalyzer(project_path)

    todos: List[TodoItem] = []
    complexity_metrics: Dict[str, float] = {}
    analyzed_files: List[str] = []

    # Analyze Python files for TODOs and complexity
    for py_file in project_path.rglob("*.py"):
        try:
            # Find TODOs
            file_todos = todo_analyzer.find_todos(py_file)
            todos.extend(file_todos)

            # Analyze complexity
            file_metrics = complexity_analyzer.analyze_file(py_file)
            complexity_metrics[str(py_file)] = sum(file_metrics.values()) / len(file_metrics) if file_metrics else 0.0

            analyzed_files.append(str(py_file))
        except Exception as e:
            print(f"Warning: Could not analyze {py_file}: {e}")
            continue

    # Analyze test coverage
    try:
        test_coverage = coverage_analyzer.analyze_coverage()
    except Exception as e:
        print(f"Warning: Could not analyze test coverage: {e}")
        test_coverage = 0.0

    # Calculate average complexity
    avg_complexity = sum(complexity_metrics.values()) / len(complexity_metrics) if complexity_metrics else 0.0

    return CodeAnalysisResult(
        todos=todos,
        complexity_metrics={"average": avg_complexity, **complexity_metrics},
        test_coverage=test_coverage,
        total_files=len(list(project_path.rglob("*.py"))),
        analyzed_files=analyzed_files,
    )

def generate_report(result: CodeAnalysisResult) -> str:
    """
    Generate a human-readable report from the analysis results.

    Args:
        result: CodeAnalysisResult to report on

    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 80)
    report.append("CODE ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"\nProject Files Analyzed: {result.total_files}")
    report.append(f"Files Successfully Analyzed: {len(result.analyzed_files)}")
    report.append(f"Test Coverage: {result.test_coverage}%")
    report.append(f"\nAverage Code Complexity: {result.complexity_metrics.get('average', 0.0):.2f}")

    if result.todos:
        report.append("\nTODO ITEMS FOUND:")
        report.append("-" * 40)
        for todo in result.todos:
            priority = f" [{todo.priority}]" if todo.priority else ""
            report.append(f"  {todo.file_path}:{todo.line_number}{priority}")
            report.append(f"    {todo.description}")
    else:
        report.append("\nNo TODO items found.")

    report.append("\n" + "=" * 80)
    return "\n".join(report)

if __name__ == "__main__":
    # Example usage and testing
    import tempfile
    import shutil

    # Create a temporary test project
    with tempfile.TemporaryDirectory() as temp_dir:
        test_project = Path(temp_dir) / "test_project"
        test_project.mkdir()

        # Create some test files
        (test_project / "main.py").write_text("""
# TODO: Implement main functionality
# FIXME(high): Fix this critical bug
def main():
    if True:
        print("Hello")  # This is a simple function
""")

        (test_project / "utils.py").write_text("""
class Utility:
    def complex_method(self):
        if True:
            if True:
                return 42
""")

        (test_project / "test_main.py").write_text("""
def test_main():
    assert True
""")

        # Run analysis
        result = aggregate_code_metrics(test_project)

        # Generate and print report
        report = generate_report(result)
        print(report)

        # Verify results
        assert len(result.todos) == 2
        assert result.test_coverage > 0
        assert result.total_files == 3
        assert len(result.analyzed_files) == 3