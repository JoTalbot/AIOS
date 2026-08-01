"""
Module for adding static code checks to CI pipeline.

This module includes steps for running mypy and ruff to ensure static code verification.
"""

import subprocess
import sys
from dataclasses import dataclass
from typing import List

@dataclass
class CodeCheckResult:
    """Result of code check."""
    command: str
    exit_code: int
    output: str

def run_code_check(command: str, target_path: str) -> CodeCheckResult:
    """
    Run code check using the given command.

    Args:
    - command: Command to run.
    - target_path: Path to target directory.

    Returns:
    - CodeCheckResult: Result of code check.
    """
    try:
        result = subprocess.run(command, capture_output=True, cwd=target_path)
        return CodeCheckResult(command, result.returncode, result.stdout.decode())
    except subprocess.CalledProcessError as e:
        return CodeCheckResult(command, e.returncode, e.output.decode())
    except Exception as e:
        print(f"An error occurred: {e}")
        return CodeCheckResult(command, 1, "An error occurred")

def install_mypy_types(target_path: str) -> CodeCheckResult:
    """
    Install mypy types.

    Args:
    - target_path: Path to target directory.

    Returns:
    - CodeCheckResult: Result of installation.
    """
    return run_code_check("mypy --install-types", target_path)

def install_ruff(target_path: str) -> CodeCheckResult:
    """
    Install ruff.

    Args:
    - target_path: Path to target directory.

    Returns:
    - CodeCheckResult: Result of installation.
    """
    return run_code_check("ruff --install", target_path)

def run_mypy(target_path: str) -> CodeCheckResult:
    """
    Run mypy.

    Args:
    - target_path: Path to target directory.

    Returns:
    - CodeCheckResult: Result of mypy run.
    """
    return run_code_check("mypy", target_path)

def run_ruff(target_path: str) -> CodeCheckResult:
    """
    Run ruff.

    Args:
    - target_path: Path to target directory.

    Returns:
    - CodeCheckResult: Result of ruff run.
    """
    return run_code_check("ruff", target_path)

if __name__ == '__main__':
    target_path = "tools"
    print("Installing mypy types...")
    mypy_types_result = install_mypy_types(target_path)
    print(f"Mypy types installation result: {mypy_types_result.command} (exit code {mypy_types_result.exit_code})")
    print(mypy_types_result.output)

    print("\nInstalling ruff...")
    ruff_result = install_ruff(target_path)
    print(f"Ruff installation result: {ruff_result.command} (exit code {ruff_result.exit_code})")
    print(ruff_result.output)

    print("\nRunning mypy...")
    mypy_result = run_mypy(target_path)
    print(f"Mypy result: {mypy_result.command} (exit code {mypy_result.exit_code})")
    print(mypy_result.output)

    print("\nRunning ruff...")
    ruff_result = run_ruff(target_path)
    print(f"Ruff result: {ruff_result.command} (exit code {ruff_result.exit_code})")
    print(ruff_result.output)

__all__ = ["install_mypy_types", "install_ruff", "run_mypy", "run_ruff"]