"""Full tests for OLX profile parser."""

from aios_core.modules.olx.profile import ProfileParser


def test_profile_parser_init():
    pp = ProfileParser()
    assert pp is not None
