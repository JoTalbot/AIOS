"""OLX profile operations tests."""
from aios_core.modules.olx.profile import ProfileParser
from aios_core.modules.olx.profile_editor import ProfileEditor
def test_profile_tools_exist():
    assert ProfileParser is not None
