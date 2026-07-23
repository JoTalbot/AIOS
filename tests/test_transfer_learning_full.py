"""Transfer learning full."""
from aios_core.transfer_learning import TransferLearner
def test(): s=TransferLearner().stats(); assert isinstance(s,dict)
