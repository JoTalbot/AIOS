"""graceful_shutdown test."""
def test(): from aios_core.graceful_shutdown import GracefulShutdown; gs = GracefulShutdown(); assert gs is not None
