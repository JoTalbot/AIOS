"""automl test."""
def test(): from aios_core.automl import AutoML; s = AutoML().stats(); assert isinstance(s, dict)
