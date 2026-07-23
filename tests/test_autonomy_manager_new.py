"""autonomy_manager test."""
def test(): from aios_core.autonomy_manager import AutonomyManager; s = AutonomyManager().stats(); assert isinstance(s, dict)
