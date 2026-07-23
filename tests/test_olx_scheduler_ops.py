"""OLX scheduler operations tests."""
from aios_core.modules.olx.scheduler import CollectionScheduler
def test_scheduler_exists():
    assert CollectionScheduler is not None
