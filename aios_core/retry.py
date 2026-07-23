"""Retry Mechanism with Exponential Backoff"""

import time
import random
from typing import Callable, Any


def retry(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = True,
) -> Any:
    """Retry a function with exponential backoff."""
    last_exception = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt == max_attempts:
                break
            sleep_time = delay
            if jitter:
                sleep_time *= 0.5 + random.random()
            time.sleep(sleep_time)
            delay *= backoff

    raise last_exception
