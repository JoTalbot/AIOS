"""Rozetka.ua detail parser — product detail page extraction."""

from __future__ import annotations

from aios_core.modules.olx.detail import AdDetailParser


class RozetkaDetailParser(AdDetailParser):
    """Parses Rozetka product detail pages from UIAutomator dumps.

    Inherits OLX AdDetailParser, Rozetka-specific markers override.
    """

