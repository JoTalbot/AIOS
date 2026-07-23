"""Text utils full."""
from aios_core.text_utils import TextProcessor
def test(): s=TextProcessor().stats(); assert isinstance(s,dict)
