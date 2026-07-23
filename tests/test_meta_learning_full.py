"""Meta learning full."""
from aios_core.meta_learning import MetaLearner
def test(): s=MetaLearner().stats(); assert isinstance(s,dict)
