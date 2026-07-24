"""Tests for aios_core/voice_interface.py"""
from __future__ import annotations
import pytest
from aios_core.voice_interface import VoiceInterface


@pytest.fixture()
def vi():
    return VoiceInterface()


class TestVoiceInterface:
    def test_create(self, vi):
        assert vi is not None

    def test_enable_disable(self, vi):
        vi.enable()
        assert vi.is_enabled() is True
        vi.disable()
        assert vi.is_enabled() is False

    def test_register_command(self, vi):
        vi.register_command(intent="search", handler=lambda text: f"searching {text}", description="Search command")

    def test_check_wake_word(self, vi):
        result = vi.check_wake_word("hey aios")
        assert isinstance(result, bool)

    def test_parse_command(self, vi):
        vi.register_command(intent="greeting", handler=lambda t: "hello")
        result = vi.parse_command("hello there")
        assert result is not None

    def test_speak(self, vi):
        vi.speak("Hello world")


    def test_get_history(self, vi):
        history = vi.get_history()
        assert isinstance(history, list)

    def test_stats(self, vi):
        s = vi.stats()
        assert isinstance(s, dict)
