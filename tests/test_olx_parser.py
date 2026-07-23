"""OLX parser tests."""
from aios_core.modules.olx.parser import CardParser
from aios_core.modules.olx.ui_parser import UIParser
def test_parsers_exist():
    assert CardParser is not None
