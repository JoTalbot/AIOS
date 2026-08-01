import re
import json
import csv
import os

from dataclasses import dataclass
from typing import List, Dict

__all__ = ['scan_repo', 'generate_report']

@dataclass
class Task:
    """Represents a task with its type and description."""
    type: str
    description: str

def scan_repo(path: str) -> List[Task]:
    """
    Scans the repository at the given path and returns a list of tasks.

    Args:
    path: The path to the repository.

    Returns:
    A list of tasks.
    """
    tasks = []
    for root, _, files in os.walk(path):
        for file in files:
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                for match in re.finditer(r'(TODO|FIXME|HACK)', content, re.IGNORECASE):
                    task_type = match.group().upper()
                    task_description = content[match.start():match.end()].strip()
                    tasks.append(Task(task_type, task_description))
    return tasks

def generate_report(tasks: List[Task], output_format: str) -> str:
    """
    Generates a report from the given tasks in the specified output format.

    Args:
    tasks: The list of tasks.
    output_format: The output format, either 'json' or 'csv'.

    Returns:
    The report in the specified format.
    """
    if output_format not in ['json', 'csv']:
        raise ValueError("Invalid output format. Must be 'json' or 'csv'.")

    if output_format == 'json':
        report = {'tasks': []}
        for task in tasks:
            report['tasks'].append({'type': task.type, 'description': task.description})
        return json.dumps(report, indent=4)
    elif output_format == 'csv':
        report = []
        for task in tasks:
            report.append([task.type, task.description])
        return '\n'.join([','.join(row) for row in report])

def main():
    path = 'path_to_your_repository'
    tasks = scan_repo(path)
    print("Number of tasks:", len(tasks))
    for task in tasks:
        print(f"{task.type}: {task.description}")

    output_format = 'json'
    report = generate_report(tasks, output_format)
    print("\nReport in", output_format, "format:")
    print(report)

if __name__ == '__main__':
    main()