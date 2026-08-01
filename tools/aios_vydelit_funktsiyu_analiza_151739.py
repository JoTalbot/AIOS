# tools/aios_vydelit_funktsiyu_analiza_151739.py

"""
Module for code analysis.
"""

from dataclasses import dataclass
from typing import List, Dict
import ast
import os

@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    file_path: str
    lines_of_code: int
    complexity: int

def analyze_code(file_path: str) -> CodeAnalysisResult:
    """
    Analyze code in a given file.

    Args:
    file_path (str): Path to the file to analyze.

    Returns:
    CodeAnalysisResult: Result of code analysis.
    """
    try:
        with open(file_path, 'r') as file:
            code = file.read()
            tree = ast.parse(code)
            lines_of_code = len(code.splitlines())
            complexity = len(tree.body)
            return CodeAnalysisResult(file_path, lines_of_code, complexity)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except Exception as e:
        print(f"Error analyzing file {file_path}: {str(e)}")
        return None

def get_code_statistics(directory_path: str) -> Dict[str, List[CodeAnalysisResult]]:
    """
    Get code statistics for all files in a given directory.

    Args:
    directory_path (str): Path to the directory to analyze.

    Returns:
    Dict[str, List[CodeAnalysisResult]]: Code statistics for each file.
    """
    try:
        statistics = {}
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                result = analyze_code(file_path)
                if result:
                    file_name = os.path.basename(file_path)
                    if file_name in statistics:
                        statistics[file_name].append(result)
                    else:
                        statistics[file_name] = [result]
        return statistics
    except Exception as e:
        print(f"Error getting code statistics: {str(e)}")
        return {}

if __name__ == '__main__':
    directory_path = 'path_to_your_directory'
    statistics = get_code_statistics(directory_path)
    for file_name, results in statistics.items():
        print(f"File: {file_name}")
        for result in results:
            print(f"  Lines of code: {result.lines_of_code}")
            print(f"  Complexity: {result.complexity}")
        print()