# tools/aios_vnesti_izmeneniya_v_145913.py

import re
import dataclasses
from typing import List, Dict
from pathlib import Path

@dataclasses.dataclass
class DebtItem:
    """Represents a debt item."""
    type: str
    description: str
    file_path: str
    line_number: int

@dataclasses.dataclass
class DebtReport:
    """Represents a debt report."""
    total_debt: int
    debt_items: List[DebtItem]

def scan_debt(target_path: Path) -> DebtReport:
    """
    Scans the target path for TODO/FIXME/HACK/XXX/BUG comments and generates a debt report.

    Args:
        target_path: The path to scan.

    Returns:
        A debt report containing the total debt and a list of debt items.
    """
    debt_items: List[DebtItem] = []
    total_debt = 0

    for file_path in target_path.rglob('*.py'):
        try:
            with file_path.open('r') as file:
                content = file.read()
                matches = re.findall(r'#\s*(TODO|FIXME|HACK|XXX|BUG)\s*[:\s].*', content, re.MULTILINE)
                for match in matches:
                    total_debt += 1
                    debt_items.append(DebtItem(
                        type=match.split(':')[0].strip(),
                        description=match.split(':')[1].strip(),
                        file_path=str(file_path),
                        line_number=content.find(match) + 1
                    ))
        except Exception as e:
            print(f"Error scanning file {file_path}: {e}")

    return DebtReport(total_debt, debt_items)

def test_scan_debt():
    """Tests the scan_debt function."""
    target_path = Path(__file__).parent
    report = scan_debt(target_path)
    assert report.total_debt > 0
    assert all(isinstance(item, DebtItem) for item in report.debt_items)

if __name__ == '__main__':
    test_scan_debt()
    report = scan_debt(Path(__file__).parent)
    print("Debt Report:")
    print(f"Total Debt: {report.total_debt}")
    for item in report.debt_items:
        print(f"{item.type}: {item.description} (File: {item.file_path}, Line: {item.line_number})")

__all__ = ['scan_debt', 'DebtItem', 'DebtReport']