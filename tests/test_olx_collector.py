"""OLX collector tests."""
from aios_core.modules.olx.collector import OLXCollector
from aios_core.modules.olx.collector_fast import FastCollector
def test_collectors_exist():
    assert OLXCollector is not None
