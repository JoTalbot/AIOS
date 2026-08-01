import git
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['scan_repository']

@dataclass
class Issue:
    """Dataclass to hold the issue information."""
    type: str
    text: str
    line: int

def scan_repository(repo_path: str) -> Dict[str, List[Issue]]:
    """
    Scan the repository for TODO/FIXME/HACK comments and return the results.

    Args:
    repo_path (str): The path to the repository.

    Returns:
    Dict[str, List[Issue]]: A dictionary with the issue types as keys and lists of Issue objects as values.
    """
    try:
        repo = git.Repo(repo_path)
        issues = {'TODO': [], 'FIXME': [], 'HACK': []}

        for file in repo.git.ls_files('-m').splitlines():
            with open(file, 'r') as f:
                for line_num, line in enumerate(f, start=1):
                    if 'TODO' in line:
                        issues['TODO'].append(Issue('TODO', line.strip(), line_num))
                    elif 'FIXME' in line:
                        issues['FIXME'].append(Issue('FIXME', line.strip(), line_num))
                    elif 'HACK' in line:
                        issues['HACK'].append(Issue('HACK', line.strip(), line_num))

        return issues
    except git.InvalidGitRepositoryError:
        print(f"Invalid Git repository at {repo_path}")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

if __name__ == '__main__':
    repo_path = 'path_to_your_repository'
    issues = scan_repository(repo_path)
    for issue_type, issue_list in issues.items():
        print(f"{issue_type.capitalize()} issues:")
        for issue in issue_list:
            print(f"  - {issue.text} (line {issue.line})")