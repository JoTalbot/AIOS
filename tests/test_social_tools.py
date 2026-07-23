"""Tests for social, tools, and general-purpose utility modules."""

from aios_core.social_intelligence import SocialIntelligence
from aios_core.tools import ToolRegistry
from aios_core.text_utils import TextProcessor
from aios_core.prompts import PromptManager
from aios_core.resources import ResourceManager


def test_social_intelligence_stats():
    s = SocialIntelligence().stats()
    assert isinstance(s, dict)


def test_tool_registry_stats():
    s = ToolRegistry().stats()
    assert isinstance(s, dict)


def test_text_processor_stats():
    s = TextProcessor().stats()
    assert isinstance(s, dict)


def test_prompt_manager_stats():
    s = PromptManager().stats()
    assert isinstance(s, dict)


def test_resource_manager_stats():
    s = ResourceManager().stats()
    assert isinstance(s, dict)
