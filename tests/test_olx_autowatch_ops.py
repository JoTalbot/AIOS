"""OLX autowatch operations tests."""
from aios_core.modules.olx.autowatch import AutoWatch
from aios_core.modules.olx.autowatch_cycle import AutoWatchCycle
def test_autowatch_exists():
    assert AutoWatch is not None
