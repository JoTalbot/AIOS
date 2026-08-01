import os
import re
import typing
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['generate_debt_report', 'scan_code_for_debt']

@dataclass
class DebtItem:
    """Class representing a debt item."""
    file_path: str
    line_number: int
    comment: str

def scan_code_for_debt(target_path: str) -> List[DebtItem]:
    """
    Scan the code in the target path for TODO/FIXME/HACK comments.

    Args:
    target_path (str): Path to the directory to scan.

    Returns:
    List[DebtItem]: List of debt items found in the code.
    """
    debt_items = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    for line_number, line in enumerate(f, 1):
                        match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
                        if match:
                            debt_items.append(DebtItem(file_path, line_number, match.group(1)))
    return debt_items

def generate_debt_report(debt_items: List[DebtItem]) -> Dict[str, int]:
    """
    Generate a debt report from the list of debt items.

    Args:
    debt_items (List[DebtItem]): List of debt items.

    Returns:
    Dict[str, int]: Debt report with TODO/FIXME/HACK counts.
    """
    report = {'TODO': 0, 'FIXME': 0, 'HACK': 0}
    for item in debt_items:
        report[item.comment] += 1
    return report

def print_debt_report(report: Dict[str, int]) -> None:
    """
    Print the debt report in a human-readable format.

    Args:
    report (Dict[str, int]): Debt report.
    """
    print('Technical Debt Report:')
    for comment, count in report.items():
        print(f'{comment}: {count}')

def integrate_with_ci_cd(report: Dict[str, int]) -> None:
    """
    Integrate the debt report with the CI/CD process.

    Args:
    report (Dict[str, int]): Debt report.
    """
    # Replace this with your actual CI/CD integration logic
    print('Integrating debt report with CI/CD process...')

if __name__ == '__main__':
    target_path = 'path/to/your/code'
    debt_items = scan_code_for_debt(target_path)
    report = generate_debt_report(debt_items)
    print_debt_report(report)
    integrate_with_ci_cd(report)