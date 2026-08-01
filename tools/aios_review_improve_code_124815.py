"""
tools/aios_review_improve_code_124815.py

This module provides a small collection of utility functions that were
originally written without type hints or robust documentation.
The functions have been refactored to include type annotations,
comprehensive docstrings, and graceful error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

__all__ = [
    "compute_factorial",
    "sum_of_squares",
    "find_max",
    "Config",
]


def compute_factorial(n: int) -> int:
    """
    Compute the factorial of a non‑negative integer.

    Parameters
    ----------
    n : int
        The number to compute the factorial of. Must be non‑negative.

    Returns
    -------
    int
        The factorial of ``n``.

    Raises
    ------
    ValueError
        If ``n`` is negative.

    Examples
    --------
    >>> compute_factorial(5)
    120
    """
    if n < 0:
        raise ValueError("n must be non‑negative")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def sum_of_squares(nums: Iterable[int]) -> int:
    """
    Return the sum of the squares of the provided integers.

    Parameters
    ----------
    nums : Iterable[int]
        An iterable of integers.

    Returns
    -------
    int
        Sum of squares of the input numbers.

    Examples
    --------
    >>> sum_of_squares([1, 2, 3])
    14
    """
    total = 0
    for num in nums:
        total += num * num
    return total


def find_max(nums: Sequence[int]) -> int:
    """
    Find the maximum value in a sequence of integers.

    Parameters
    ----------
    nums : Sequence[int]
        A non‑empty sequence of integers.

    Returns
    -------
    int
        The maximum integer in ``nums``.

    Raises
    ------
    ValueError
        If ``nums`` is empty.

    Examples
    --------
    >>> find_max([10, 20, 5])
    20
    """
    if not nums:
        raise ValueError("Cannot find maximum of an empty sequence")
    max_val = nums[0]
    for num in nums[1:]:
        if num > max_val:
            max_val = num
    return max_val


@dataclass(frozen=True)
class Config:
    """
    Configuration holder for the utility functions.

    Attributes
    ----------
    max_factorial : int
        The maximum value for which factorial will be computed.
    """

    max_factorial: int = 20

    def validate(self) -> None:
        """
        Validate the configuration.

        Raises
        ------
        ValueError
            If ``max_factorial`` is negative.
        """
        if self.max_factorial < 0:
            raise ValueError("max_factorial must be non‑negative")


if __name__ == "__main__":
    # Simple test harness
    import sys

    def _run_tests() -> None:
        try:
            assert compute_factorial(0) == 1
            assert compute_factorial(5) == 120
            assert sum_of_squares([1, 2, 3]) == 14
            assert find_max([10, 20, 5]) == 20
            cfg = Config(max_factorial=30)
            cfg.validate()
            print("All tests passed.")
        except AssertionError as exc:
            print("Test failed:", exc, file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print("Unexpected error:", exc, file=sys.stderr)
            sys.exit(1)

    _run_tests()