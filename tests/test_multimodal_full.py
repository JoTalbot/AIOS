"""Multimodal full ops."""
from aios_core.multimodal import MultimodalProcessor
def test_mp(): s=MultimodalProcessor().stats(); assert isinstance(s,dict)
