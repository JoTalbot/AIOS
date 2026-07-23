"""Self-supervised full."""
from aios_core.self_supervised import SelfSupervisedLearner
def test(): s=SelfSupervisedLearner().stats(); assert isinstance(s,dict)
