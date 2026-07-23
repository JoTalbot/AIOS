"""Android recorder ops."""
from aios_core.android_recorder import ScenarioRecorder, RecordedStep
def test_step(): rs = RecordedStep("tap", {"x": 10}); assert rs.action == "tap"
