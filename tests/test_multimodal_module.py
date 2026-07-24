"""Tests for aios_core/multimodal.py"""
from __future__ import annotations
import pytest
from aios_core.multimodal import MultiModalProcessor


@pytest.fixture()
def proc():
    return MultiModalProcessor()


class TestMultiModalProcessor:
    def test_create(self, proc):
        assert proc is not None

    def test_register_modality(self, proc):
        proc.register_modality(name="text", embedding_dim=128)

    def test_unregister_modality(self, proc):
        proc.register_modality(name="temp", embedding_dim=64)
        proc.unregister_modality("temp")

    def test_get_modality(self, proc):
        proc.register_modality(name="text", embedding_dim=128)
        m = proc.get_modality("text")
        assert m is not None

    def test_process_text(self, proc):
        result = proc.process_text("hello world")
        assert result is not None
        assert isinstance(result, (list, dict, tuple))

    def test_process_image(self, proc):
        result = proc.process_image(features=[0.1, 0.2, 0.3])
        assert result is not None

    def test_stats(self, proc):
        s = proc.stats()
        assert isinstance(s, dict)
