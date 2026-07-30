"""
Run Coder Orchestrator Module

This module provides functionality to run and manage coder orchestrators.
It includes version control capabilities using git.

Changes:
- Initial creation of the module with basic functionality
- Added git version control capabilities
- Implemented self-contained structure with testing block
- Moved from root to tools/run_coder_orchestrator.py
- Added type hints and improved docstrings
- Added technical debt scanning functionality integrated with logging and notification
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

__all__ = ["CoderOrchestrator", "run_orchestrator", "get_git_version", "scan_technical_debt", "report_technical_debt"]


@dataclass
class CoderOrchestrator:
    """Class representing a coder orchestrator.

    Attributes:
        name: The name of the orchestrator.
        config: Configuration dictionary for the orchestrator.
        version: Version of the orchestrator, defaults to "1.0.0".
    """

    name: str
    config: Dict[str, Any]
    version: str = "1.0.0"

    def run(self) -> None:
        """Run the coder orchestrator with the given configuration.

        Prints the orchestrator name and its configuration.
        """
        print(f"Running orchestrator {self.name} with config: {self.config}")


def run_orchestrator(orchestrator: CoderOrchestrator) -> None:
    """Run a given coder orchestrator.

    Args:
        orchestrator: The orchestrator to run.
    """
    orchestrator.run()


def get_git_version(file_path: Path) -> Optional[str]:
    """Get the git version of a file.

    Args:
        file_path: Path to the file to check.

    Returns:
        The git version hash if available, None otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=file_path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Root cause: This exception occurs when the git command fails, typically because the directory is not a git repository
        logging.error(f"Error getting git version: {e}")
        return None
    except Exception as e:
        logging.error(f"Error getting git version: {e}")
        return None


def scan_technical_debt(
    root_path: Path,
) -> List[Tuple[Path, int, str]]:
    """Scan all Python files in the project for technical debt tags.

    Searches for tags: TODO, FIXME, HACK, XXX, BUG in comments.

    Args:
        root_path: The root directory of the project to scan.

    Returns:
        A list of tuples containing:
            - Path to the file containing the tag
            - Line number where the tag was found
            - The full comment text containing the tag
    """
    tags = {"TODO", "FIXME", "HACK", "XXX", "BUG"}
    results: List[Tuple[Path, int, str]] = []

    try:
        for py_file in root_path.rglob("*.py"):
            try:
                with py_file.open("r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, start=1):
                        stripped_line = line.strip()
                        # Check if line contains a comment with any of the tags
                        if "#" in stripped_line:
                            comment_index = stripped_line.find("#")
                            comment_text = stripped_line[comment_index + 1 :].strip()
                            # Check if any tag is in the comment text (case-insensitive)
                            if any(tag in comment_text.upper() for tag in tags):
                                results.append((py_file, line_num, comment_text))
            except (OSError, UnicodeDecodeError) as e:
                logging.warning(f"Could not read file {py_file}: {e}")
    except Exception as e:
        logging.error(f"Error scanning files: {e}")

    return results


def report_technical_debt(
    entries: List[Tuple[Path, int, str]],
    to_console: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Report the technical debt entries to console and/or logger.

    Args:
        entries: List of technical debt entries as tuples (file, line, comment).
        to_console: Whether to print the report to the console.
        logger: Optional logger to log the report.
    """
    if not entries:
        message = "No technical debt tags found."
        if to_console:
            print(message)
        if logger:
            logger.info(message)
        return

    header = "\nTechnical Debt Report:"
    if to_console:
        print(header)
    if logger:
        logger.info(header)

    for file, line_num, comment in entries:
        line = f"{file}:{line_num}: {comment}"
        if to_console:
            print(line)
        if logger:
            logger.warning(line)

    # Basic notification to the team via logging
    notification = f"Technical debt scan completed with {len(entries)} issues found."
    if logger:
        logger.info(notification)


def main() -> None:
    """Main function for testing the module.

    Creates an example orchestrator, runs it, checks the git version,
    and scans the project for technical debt tags, reporting the results.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    # Example usage
    orchestrator = CoderOrchestrator(
        name="Test Orchestrator",
        config={"param1": "value1", "param2": "value2"},
    )
    run_orchestrator(orchestrator)

    # Get git version
    file_path = Path(__file__)
    version = get_git_version(file_path)
    if version:
        logger.info(f"Current git version: {version}")
    else:
        logger.warning("Could not determine git version.")

    # Determine project root directory
    project_root = file_path.parent.parent if file_path.parent.name == "tools" else file_path.parent

    # Scan for technical debt tags
    technical_debt_entries = scan_technical_debt(project_root)

    # Report technical debt
    report_technical_debt(technical_debt_entries, to_console=True, logger=logger)


if __name__ == "__main__":
    main()