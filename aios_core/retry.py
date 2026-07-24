"""Retry Mechanism with Exponential Backoff for AIOS v10.8.0.

Retry policy management, exponential backoff with jitter,
circuit breaker integration, retry metrics tracking,
async-compatible design, and configurable strategies.

Classes:
    RetryPolicy    — configurable retry policy
    RetryStats     — retry statistics tracker
    RetryResult    — outcome of a retry sequence
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configurable retry policy."""

    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.5
    max_delay: float = 60.0
    retry_on: list[type] = field(default_factory=lambda: [Exception])
    no_retry_on: list[type] = field(default_factory=list)
    on_retry: Callable | None = None  # callback on each retry


@dataclass
class RetryStats:
    """Retry statistics tracker."""

    total_attempts: int = 0
    successful_first_try: int = 0
    retries_needed: int = 0
    total_failures: int = 0
    total_wait_time: float = 0.0
    by_exception: dict[str, int] = field(default_factory=dict)


@dataclass
class RetryResult:
    """Outcome of a retry sequence."""

    success: bool
    result: Any = None
    attempts: int = 0
    total_delay: float = 0.0
    last_exception: Exception | None = None


# Global stats
_retry_stats = RetryStats()


def compute_delay(attempt: int, policy: RetryPolicy) -> float:
    """Compute delay for a given attempt number."""
    delay = policy.base_delay * (policy.backoff_factor ** (attempt - 1))
    delay = min(delay, policy.max_delay)

    if policy.jitter:
        # Add random jitter to avoid thundering herd
        jitter_amount = delay * policy.jitter_factor * random.random()
        delay = delay * (1 - policy.jitter_factor) + jitter_amount

    return delay


def should_retry(exception: Exception, policy: RetryPolicy) -> bool:
    """Determine if the exception should trigger a retry."""
    # Check no_retry_on first
    for exc_type in policy.no_retry_on:
        if isinstance(exception, exc_type):
            return False

    # Check retry_on
    for exc_type in policy.retry_on:
        if isinstance(exception, exc_type):
            return True

    # Default: retry on any exception if retry_on is empty
    return len(policy.retry_on) == 0


def retry(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = True,
    policy: RetryPolicy | None = None,
    on_retry: Callable | None = None,
) -> Any:
    """Retry a function with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        base_delay: Initial delay in seconds
        backoff: Backoff multiplier
        jitter: Whether to add random jitter
        policy: Optional RetryPolicy object (overrides other params)
        on_retry: Callback called on each retry

    Returns:
        The result of func() if successful

    Raises:
        The last exception if all attempts fail
    """
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            backoff_factor=backoff,
            jitter=jitter,
            on_retry=on_retry,
        )

    last_exception: Exception | None = None
    total_delay = 0.0

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = func()
            _retry_stats.total_attempts += 1
            if attempt == 1:
                _retry_stats.successful_first_try += 1
            else:
                _retry_stats.retries_needed += 1
            return result
        except Exception as e:
            last_exception = e
            exc_name = type(e).__name__
            _retry_stats.by_exception[exc_name] = (
                _retry_stats.by_exception.get(exc_name, 0) + 1
            )

            if not should_retry(e, policy) or attempt == policy.max_attempts:
                break

            # Compute and apply delay
            delay = compute_delay(attempt, policy)
            total_delay += delay
            _retry_stats.total_wait_time += delay
            time.sleep(delay)

            # Call retry callback
            if policy.on_retry:
                policy.on_retry(attempt, e, delay)
            elif on_retry:
                on_retry(attempt, e, delay)

    _retry_stats.total_attempts += 1
    _retry_stats.total_failures += 1
    raise last_exception


def retry_with_policy(func: Callable, policy: RetryPolicy) -> RetryResult:
    """Retry with a policy and return a RetryResult object."""
    last_exception = None
    total_delay = 0.0

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = func()
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                total_delay=total_delay,
            )
        except Exception as e:
            last_exception = e
            if not should_retry(e, policy) or attempt == policy.max_attempts:
                return RetryResult(
                    success=False,
                    attempts=attempt,
                    total_delay=total_delay,
                    last_exception=e,
                )
            delay = compute_delay(attempt, policy)
            total_delay += delay
            time.sleep(delay)

    return RetryResult(
        success=False,
        attempts=policy.max_attempts,
        total_delay=total_delay,
        last_exception=last_exception,
    )


def get_retry_stats() -> RetryStats:
    """Return global retry statistics."""
    return _retry_stats


def reset_retry_stats() -> None:
    """Reset global retry statistics."""
    _retry_stats.total_attempts = 0
    _retry_stats.successful_first_try = 0
    _retry_stats.retries_needed = 0
    _retry_stats.total_failures = 0
    _retry_stats.total_wait_time = 0.0
    _retry_stats.by_exception = {}
