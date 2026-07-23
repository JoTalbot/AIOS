"""AutoML full ops."""
from aios_core.automl import AutoML
def test(): s=AutoML().stats(); assert isinstance(s,dict)
