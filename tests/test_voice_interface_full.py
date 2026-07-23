"""Voice interface full."""
from aios_core.voice_interface import VoiceInterface
def test(): s=VoiceInterface().stats(); assert isinstance(s,dict)
