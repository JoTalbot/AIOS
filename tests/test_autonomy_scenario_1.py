from aios_core.autonomy_manager import AutonomyManager
def test(): s = AutonomyManager().stats(); assert isinstance(s, dict)
