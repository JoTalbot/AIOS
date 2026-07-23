"""multimodal test."""
def test(): from aios_core.multimodal import MultimodalProcessor; s = MultimodalProcessor().stats(); assert isinstance(s, dict)
