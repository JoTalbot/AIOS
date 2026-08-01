from dataclasses import dataclass
from typing import List, Dict
import re
import os

__all__ = ['scan_code', 'generate_report', 'test']

@dataclass
class DebtItem:
    """Class to represent a debt item."""
    tag: str
    line_number: int
    file_path: str

def scan_code(file_path: str) -> List[DebtItem]:
    """
    Scan the code in the given file for TODO/FIXME/HACK tags.

    Args:
    file_path (str): Path to the file to scan.

    Returns:
    List[DebtItem]: List of debt items found in the file.
    """
    debt_items = []
    try:
        with open(file_path, 'r') as file:
            for line_number, line in enumerate(file, start=1):
                for tag in ['TODO', 'FIXME', 'HACK']:
                    if re.search(r'\b' + tag + r'\b', line):
                        debt_items.append(DebtItem(tag, line_number, file_path))
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    return debt_items

def generate_report(debt_items: List[DebtItem]) -> Dict[str, int]:
    """
    Generate a report from the given debt items.

    Args:
    debt_items (List[DebtItem]): List of debt items.

    Returns:
    Dict[str, int]: Report with the count of each debt item type.
    """
    report = {}
    for item in debt_items:
        if item.tag in report:
            report[item.tag] += 1
        else:
            report[item.tag] = 1
    return report

def test():
    """
    Test the scan_code and generate_report functions.
    """
    test_file_path = 'test.txt'
    with open(test_file_path, 'w') as file:
        file.write('# TODO: This is a TODO comment\n')
        file.write('# FIXME: This is a FIXME comment\n')
        file.write('# HACK: This is a HACK comment\n')

    debt_items = scan_code(test_file_path)
    report = generate_report(debt_items)
    print(report)

    # Clean up the test file
    os.remove(test_file_path)

if __name__ == '__main__':
    test()