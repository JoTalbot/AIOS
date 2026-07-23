"""Tests for OLX UI parser, login, competitive, and autowatch."""

from aios_core.modules.olx.ui_parser import OLXUIParser
from aios_core.modules.olx.login import OLXLoginDriver
from aios_core.modules.olx.competitive import CompetitorAnalyzer


def test_ui_parser_init():
    p = OLXUIParser()
    assert p is not None


def test_login_driver_init():
    d = OLXLoginDriver()
    assert d is not None


def test_competitor_analyzer_init():
    a = CompetitorAnalyzer()
    assert a is not None
