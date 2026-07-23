"""Graceful Shutdown Handler for AIOS"""

import asyncio
import logging
import signal
import sys
from typing import Callable, List

__all__ = ["GracefulShutdown", "shutdown_handler"]

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handles graceful shutdown of AIOS services."""

    def __init__(self):
        self.shutdown_handlers: List[Callable] = []
        self._shutdown_event = asyncio.Event()

    def register_handler(self, handler: Callable) -> None:
        self.shutdown_handlers.append(handler)

    def _signal_handler(self, sig, frame):
        logger.info("Received signal %s — shutting down gracefully", sig)
        self._shutdown_event.set()
        for handler in self.shutdown_handlers:
            try:
                handler()
            except Exception as e:
                logger.error("Shutdown handler error: %s", e)
        sys.exit(0)

    def setup(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def wait_for_shutdown(self) -> None:
        await self._shutdown_event.wait()


shutdown_handler = GracefulShutdown()
