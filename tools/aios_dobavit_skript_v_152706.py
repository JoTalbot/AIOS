"""
Module for adding a CI script to run mypy and ruff.

This module is designed to be self-contained and can be used as a standalone script.
It includes an `__all__` export list and a test block for running the script directly.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class CiConfig:
    """Configuration for the CI script."""
    on: str
    jobs: str
    steps: List[str]

    def __post_init__(self):
        """Initialize the CI configuration."""
        self.on = self.on.strip()
        self.jobs = self.jobs.strip()
        self.steps = [step.strip() for step in self.steps]

def generate_ci_script():
    """
    Generate the CI script for running mypy and ruff.

    Returns:
        str: The generated CI script.
    """
    ci_config = CiConfig(
        on="push: branches: [ main ]",
        jobs="""
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
        """,
        steps="""
          - name: Checkout code
            uses: actions/checkout@v2
          - name: Install dependencies
            run: pip install mypy ruff
          - name: Run mypy
            run: mypy .
          - name: Run ruff
            run: ruff .
        """
    )

    return ci_config.jobs + ci_config.steps

def main():
    """
    Test the CI script generation.

    This function generates the CI script and prints it to the console.
    """
    ci_script = generate_ci_script()
    print(ci_script)

if __name__ == '__main__':
    main()

__all__ = ["CiConfig", "generate_ci_script"]