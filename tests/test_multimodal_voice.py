"""Tests for multimodal, voice, and natural language modules."""

from aios_core.multimodal import MultimodalProcessor
from aios_core.voice_interface import VoiceInterface
from aios_core.natural_language import NLProcessor


def test_multimodal_processor_stats():
    mp = MultimodalProcessor()
    s = mp.stats()
    assert isinstance(s, dict)


def test_voice_interface_stats():
    vi = VoiceInterface()
    s = vi.stats()
    assert isinstance(s, dict)


def test_nl_processor_stats():
    nlp = NLProcessor()
    s = nlp.stats()
    assert isinstance(s, dict)
