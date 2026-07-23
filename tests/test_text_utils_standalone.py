"""text_utils standalone test."""
from aios_core.text_utils import TextProcessor
def test_init(): s = TextProcessor().stats(); assert isinstance(s, dict)
