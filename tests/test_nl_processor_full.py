"""NL processor full."""
from aios_core.natural_language import NLProcessor
def test(): s=NLProcessor().stats(); assert isinstance(s,dict)
