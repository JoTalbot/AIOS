"""
Module for adding a secrets scanner to the CI pipeline.

This module uses the secrets-scanner library to scan for secrets in all files of the project.
"""

import os
from dataclasses import dataclass
from typing import Optional

import secrets_scanner

@dataclass
class SecretsScannerConfig:
    """Configuration for the secrets scanner."""
    project_dir: str
    output_dir: str = "secrets_scanner_output"

def configure_gitignore(project_dir: str) -> None:
    """
    Configure the .gitignore file to ignore the secrets scanner output directory.

    Args:
        project_dir: The path to the project directory.
    """
    gitignore_path = os.path.join(project_dir, ".gitignore")
    with open(gitignore_path, "a") as f:
        f.write("\n# Secrets scanner output directory\n")
        f.write(f"{SecretsScannerConfig(output_dir=SecretsScannerConfig.output_dir).output_dir}/\n")

def configure_github_workflow(project_dir: str) -> None:
    """
    Configure the .github/workflows/main.yml file to run the secrets scanner.

    Args:
        project_dir: The path to the project directory.
    """
    workflow_path = os.path.join(project_dir, ".github", "workflows", "main.yml")
    with open(workflow_path, "a") as f:
        f.write("\n# Secrets scanner step\n")
        f.write("  - name: Secrets scanner\n")
        f.write("    run: |\n")
        f.write("      python -c \"import secrets_scanner; secrets_scanner.scan_files('{project_dir}')\"\n".format(project_dir=project_dir))

def scan_secrets(project_dir: str) -> None:
    """
    Scan for secrets in all files of the project.

    Args:
        project_dir: The path to the project directory.
    """
    try:
        secrets_scanner.scan_files(project_dir)
    except Exception as e:
        print(f"Error scanning for secrets: {e}")

def main() -> None:
    """
    Main function for testing.
    """
    project_dir = os.path.dirname(os.path.abspath(__file__))
    configure_gitignore(project_dir)
    configure_github_workflow(project_dir)
    scan_secrets(project_dir)

if __name__ == "__main__":
    main()