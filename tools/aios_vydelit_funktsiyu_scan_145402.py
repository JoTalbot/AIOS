# tools/aios_vydelit_funktsiyu_scan_145402.py

"""
Module for analyzing code for TODO, FIXME, and HACK comments.
"""

from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    todo_count: int
    fixme_count: int
    hack_count: int

def scan_for_todo_fixme_hack(code: str) -> CodeAnalysisResult:
    """
    Scan the given code for TODO, FIXME, and HACK comments.

    Args:
        code: The code to analyze.

    Returns:
        CodeAnalysisResult: The result of the analysis.
    """
    todo_count = len(re.findall(r'# TODO', code, re.MULTILINE))
    fixme_count = len(re.findall(r'# FIXME', code, re.MULTILINE))
    hack_count = len(re.findall(r'# HACK', code, re.MULTILINE))

    return CodeAnalysisResult(todo_count, fixme_count, hack_count)

__all__ = ['scan_for_todo_fixme_hack']

if __name__ == '__main__':
    # Test the function
    code = """
# TODO: Implement this feature
# FIXME: This code is broken
# HACK: This is a hack
"""
    result = scan_for_todo_fixme_hack(code)
    print(f"TODO: {result.todo_count}")
    print(f"FIXME: {result.fixme_count}")
    print(f"HACK: {result.hack_count}")