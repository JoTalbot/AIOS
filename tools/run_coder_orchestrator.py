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
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

__all__ = ["CoderOrchestrator", "run_orchestrator", "get_git_version"]

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
        print(f"Error getting git version: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting git version: {e}", file=sys.stderr)
        return None

def main() -> None:
    """Main function for testing the module.

    Creates an example orchestrator, runs it, and checks the git version.
    """
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
        print(f"Current git version: {version}")
    else:
        print("Could not determine git version.")

if __name__ == "__main__":
    main()