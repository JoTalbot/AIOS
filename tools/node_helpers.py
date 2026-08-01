"""
Module for analyzing code and scanning files.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import unittest

@dataclass
class Tag:
    """Dataclass for storing a tag."""
    name: str
    value: str

def scan_for_tags(file_path: Path) -> list[Tag]:
    """
    Scan a file for tags in the format `# <tag_name> <tag_value>`.

    Args:
        file_path: Path to the file to scan.

    Returns:
        List of tags found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            tags = re.findall(r'# (\w+) (\w+)', content)
            return [Tag(tag[0], tag[1]) for tag in tags]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def analyze_code(file_path: Path) -> dict[str, str]:
    """
    Analyze the code in a file and return a dictionary with the results.

    Args:
        file_path: Path to the file to analyze.

    Returns:
        Dictionary with the analysis results.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            # Simple analysis: count the number of lines and characters
            lines = content.count('\n')
            chars = len(content)
            return {'lines': str(lines), 'chars': str(chars)}
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return {}
    except Exception as e:
        print(f"Error analyzing file {file_path}: {e}")
        return {}

class TestCodeAnalysis(unittest.TestCase):
    """Tests for the code analysis functions."""

    def test_scan_for_tags(self):
        """Test scanning for tags in a file."""
        file_path = Path('test.txt')
        with open(file_path, 'w') as file:
            file.write('# tag1 value1\n# tag2 value2')
        tags = scan_for_tags(file_path)
        self.assertEqual(tags, [Tag('tag1', 'value1'), Tag('tag2', 'value2')])
        file_path.unlink()

    def test_analyze_code(self):
        """Test analyzing a file."""
        file_path = Path('test.txt')
        with open(file_path, 'w') as file:
            file.write('This is a test file.\nIt has multiple lines.')
        analysis = analyze_code(file_path)
        self.assertEqual(analysis, {'lines': '2', 'chars': '34'})
        file_path.unlink()

if __name__ == '__main__':
    unittest.main()