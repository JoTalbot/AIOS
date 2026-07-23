"""voice_interface test."""
def test(): from aios_core.voice_interface import VoiceInterface; s = VoiceInterface().stats(); assert isinstance(s, dict)
