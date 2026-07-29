import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


class WebhookRetryHandler:
    def __init__(self, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.dead_letters = []
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries:
                    await self._send_to_dead_letter(func, args, kwargs, str(e))
                    raise
                
                delay = self.base_delay * (2 ** attempt)
                print(f"[Retry] Attempt {attempt + 1} failed, retrying in {delay}s...")
                await asyncio.sleep(delay)
    
    async def _send_to_dead_letter(self, func, args, kwargs, error: str):
        self.dead_letters.append({
            "func": func.__name__,
            "args": str(args),
            "kwargs": str(kwargs),
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "retry_count": self.max_retries
        })
        print(f"[DeadLetter] Message sent to DLQ: {error}")
    
    def get_dead_letters(self):
        return self.dead_letters
    
    async def retry_dead_letter(self, index: int):
        if 0 <= index < len(self.dead_letters):
            self.dead_letters.pop(index)
            print(f"[DeadLetter] Retrying message {index}")
            return True
        return False

retry_handler = WebhookRetryHandler(max_retries=3, base_delay=1.0)
