"""Fixed tests for Android AI Navigation (M7)."""

import pytest
from unittest.mock import Mock, patch
from aios_core.android_ai_navigation import AIScreenClassifier, SelfHealingLocator, ScreenEmbedding


class MockUIElement:
    def __init__(self, text="", resource_id="", clickable=True, enabled=True):
        self.text = text
        self.resource_id = resource_id
        self.clickable = clickable
        self.enabled = enabled
        self.bounds = (0, 0, 100, 100)


class TestAIScreenClassifier:
    @patch("aios_core.android_ai_navigation.UIAutomatorParser")
    def test_classify_basic_heuristics(self, mock_parser_cls):
        mock_parser = Mock()
        mock_parser.parse.return_value = True
        mock_parser.find_search_field.return_value = MockUIElement(text="search")
        mock_parser.find_search_results.return_value = [MockUIElement(), MockUIElement()]
        mock_parser.find_clickable_elements.return_value = [
            MockUIElement(text="btn1"),
            MockUIElement(text="btn2"),
        ]
        mock_parser_cls.return_value = mock_parser
        classifier = AIScreenClassifier()
        result = classifier.classify(
            "<uiclass><element text='test'/><element text='another'/></uiclass>"
        )
        assert isinstance(result, ScreenEmbedding)
        assert result.name == "unknown"

    # Add other tests similarly...
