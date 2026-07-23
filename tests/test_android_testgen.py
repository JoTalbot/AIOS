"""Tests for Android test generator and recorder."""

from aios_core.android_test_generator import TestGenerator
from aios_core.android_recorder import ScenarioRecorder


def test_test_generator_init():
    tg = TestGenerator()
    assert tg is not None


def test_scenario_recorder_init():
    sr = ScenarioRecorder()
    assert sr is not None


def test_scenario_recorder_stats():
    sr = ScenarioRecorder()
    s = sr.stats()
    assert isinstance(s, dict)
