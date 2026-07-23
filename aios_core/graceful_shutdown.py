"""Graceful Shutdown Handler for AIOS"""

import asyncio
import signal
import sys
from typing import Callable, List


class GracefulShutdown:
    """Handles graceful shutdown of AIOS services."""

    def __init__(self):
        self.shutdown_handlers: List[Callable] = []
        self._shutdown_event = asyncio.Event()

    def register_handler(self, handler: Callable):
        self.shutdown_handlers.append(handler)

    def _signal_handler(self, sig, frame):
        print(f"\nReceived signal {sig}. Shutting down gracefully...")
        self._shutdown_event.set()
        for handler in self.shutdown_handlers:
            try:
                handler()
            except Exception as e:
                print(f"Shutdown handler error: {e}")
        sys.exit(0)

    def setup(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def wait_for_shutdown(self):
        await self._shutdown_event.wait()


shutdown_handler = GracefulShutdown()
