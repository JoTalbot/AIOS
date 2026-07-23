"""test_voice_multimodal_scenario test."""
from aios_core.voice_interface import VoiceInterface
from aios_core.multimodal import MultimodalProcessor
from aios_core.natural_language import NLProcessor

def test_voice_multimodal():
    for o in [VoiceInterface(), MultimodalProcessor(), NLProcessor()]:
        s = o.stats()
        assert isinstance(s, dict)

