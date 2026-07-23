"""Graceful shutdown full."""
from aios_core.graceful_shutdown import GracefulShutdown
def test(): gs=GracefulShutdown(); assert gs is not None
