"""Tests for multimodal, embodied AI, brain-computer, and personalization."""

from aios_core.embodied_ai import EmbodiedAgent
from aios_core.brain_computer import BrainComputerInterface
from aios_core.personalization import PersonalizationEngine
from aios_core.sustainability import SustainabilityTracker
from aios_core.time_series import TimeSeriesAnalyzer


def test_embodied_agent_stats():
    s = EmbodiedAgent().stats()
    assert isinstance(s, dict)


def test_brain_computer_stats():
    s = BrainComputerInterface().stats()
    assert isinstance(s, dict)


def test_personalization_stats():
    s = PersonalizationEngine().stats()
    assert isinstance(s, dict)


def test_sustainability_stats():
    s = SustainabilityTracker().stats()
    assert isinstance(s, dict)


def test_time_series_stats():
    s = TimeSeriesAnalyzer().stats()
    assert isinstance(s, dict)
