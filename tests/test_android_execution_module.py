"""Tests for aios_core/android_execution.py"""
from __future__ import annotations
import pytest
from aios_core.android_execution import UIElement, UIAutomatorParser


SAMPLE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
  <node resource-id="com.app:id/search" text="" class="android.widget.EditText" 
        bounds="[0,0][100,50]" clickable="true" enabled="true" package="com.app" />
  <node resource-id="com.app:id/title" text="iPhone 15" class="android.widget.TextView" 
        bounds="[0,60][200,100]" clickable="false" enabled="true" package="com.app" />
</hierarchy>'''


class TestUIElement:
    def test_create(self):
        el = UIElement(resource_id="r1", text="hello", class_name="TextView",
                       bounds=(0, 0, 100, 50), clickable=True, enabled=True, package="com.app")
        assert el.resource_id == "r1"
        assert el.text == "hello"

    def test_center(self):
        el = UIElement(resource_id="r1", text="", class_name="View",
                       bounds=(0, 0, 100, 50), clickable=False, enabled=True, package="com.app")
        cx, cy = el.center
        assert cx == 50
        assert cy == 25

    def test_matches_text(self):
        el = UIElement(resource_id="r1", text="iPhone 15", class_name="TV",
                       bounds=(0, 0, 100, 50), clickable=False, enabled=True, package="com.app")
        assert el.matches_text("iphone") is True
        assert el.matches_text("Samsung") is False

    def test_matches_resource(self):
        el = UIElement(resource_id="com.app:id/search", text="", class_name="ET",
                       bounds=(0, 0, 100, 50), clickable=True, enabled=True, package="com.app")
        assert el.matches_resource("search") is True
        assert el.matches_resource("button") is False


class TestUIAutomatorParser:
    def test_create(self):
        parser = UIAutomatorParser(SAMPLE_XML)
        assert parser is not None

    def test_parse_returns_bool(self):
        parser = UIAutomatorParser(SAMPLE_XML)
        result = parser.parse()
        assert isinstance(result, bool)
