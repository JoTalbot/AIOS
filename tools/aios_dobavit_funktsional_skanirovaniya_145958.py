# tools/aios_dobavit_funktsional_skanirovaniya_145958.py

import re
import os
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['find_todo_fixme_hack', 'scan_code']

@dataclass
class CodeScanResult:
    """Result of code scan."""
    file_path: str
    lines: List[str]
    comments: List[str]

def find_todo_fixme_hack(lines: List[str]) -> List[str]:
    """
    Find TODO/FIXME/HACK comments in the given lines of code.

    Args:
    lines (List[str]): Lines of code to scan.

    Returns:
    List[str]: List of TODO/FIXME/HACK comments found.
    """
    pattern = r'#\s*(TODO|FIXME|HACK)'
    return [line for line in lines if re.search(pattern, line, re.IGNORECASE)]

def scan_code(target_path: str) -> Dict[str, CodeScanResult]:
    """
    Scan code in the given target path and find TODO/FIXME/HACK comments.

    Args:
    target_path (str): Path to the directory to scan.

    Returns:
    Dict[str, CodeScanResult]: Dictionary with file paths as keys and scan results as values.
    """
    results = {}
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                comments = find_todo_fixme_hack(lines)
                results[file_path] = CodeScanResult(
                    file_path=file_path,
                    lines=[line.strip() for line in lines],
                    comments=comments
                )
    return results

def main():
    import unittest
    from unittest.mock import patch
    from tempfile import TemporaryDirectory

    class TestCodeScan(unittest.TestCase):
        def test_find_todo_fixme_hack(self):
            lines = [
                '# TODO: This is a TODO comment',
                '# FIXME: This is a FIXME comment',
                '# HACK: This is a HACK comment',
                'print("Hello World!")'
            ]
            self.assertEqual(find_todo_fixme_hack(lines), [
                '# TODO: This is a TODO comment',
                '# FIXME: This is a FIXME comment',
                '# HACK: This is a HACK comment'
            ])

        @patch('os.walk')
        def test_scan_code(self, mock_walk):
            mock_walk.return_value = [
                ('/path/to/dir', ['subdir'], ['file1.py', 'file2.py']),
                ('/path/to/dir/subdir', [], ['file3.py'])
            ]
            with TemporaryDirectory() as tmpdir:
                os.mkdir(os.path.join(tmpdir, 'subdir'))
                with open(os.path.join(tmpdir, 'file1.py'), 'w') as f:
                    f.write('# TODO: This is a TODO comment\nprint("Hello World!")')
                with open(os.path.join(tmpdir, 'file2.py'), 'w') as f:
                    f.write('# FIXME: This is a FIXME comment\nprint("Hello World!")')
                with open(os.path.join(tmpdir, 'file3.py'), 'w') as f:
                    f.write('# HACK: This is a HACK comment\nprint("Hello World!")')
                results = scan_code(tmpdir)
                self.assertEqual(len(results), 3)
                self.assertIn('/path/to/dir/file1.py', results)
                self.assertIn('/path/to/dir/file2.py', results)
                self.assertIn('/path/to/dir/subdir/file3.py', results)

    unittest.main(argv=[__file__])

if __name__ == '__main__':
    main()