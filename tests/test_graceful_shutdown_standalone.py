"""graceful_shutdown test."""
from aios_core.graceful_shutdown import GracefulShutdown
def test_init(): assert GracefulShutdown() is not None
