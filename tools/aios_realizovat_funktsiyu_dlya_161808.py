"""
Module for scanning code for TODO/FIXME/HACK comments and adding tests for its functionality.
"""

import re
import os
from dataclasses import dataclass
from typing import List, Tuple

__all__ = ["scan_code", "TestScanCode"]

@dataclass
class ScanResult:
    """Dataclass for storing scan results."""
    file_path: str
    line_number: int
    comment: str

def scan_code(target_path: str) -> List[ScanResult]:
    """
    Scan code for TODO/FIXME/HACK comments.

    Args:
    target_path (str): Path to the directory to scan.

    Returns:
    List[ScanResult]: List of scan results.
    """
    results = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        for line_number, line in enumerate(f, start=1):
                            if re.search(r"TODO|FIXME|HACK", line, re.IGNORECASE):
                                results.append(ScanResult(file_path, line_number, line.strip()))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
    return results

class TestScanCode:
    """Test class for scan_code function."""

    def test_scan_code(self):
        """Test scan_code function with a sample directory."""
        target_path = "tests/sample_dir"
        results = scan_code(target_path)
        assert len(results) == 3
        assert results[0].file_path == os.path.join(target_path, "file1.py")
        assert results[0].line_number == 2
        assert results[0].comment == "TODO: This is a TODO comment"

    def test_scan_code_empty_dir(self):
        """Test scan_code function with an empty directory."""
        target_path = "tests/empty_dir"
        results = scan_code(target_path)
        assert len(results) == 0

if __name__ == "__main__":
    test = TestScanCode()
    test.test_scan_code()
    test.test_scan_code_empty_dir()
    print("All tests passed.")