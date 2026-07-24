"""Rozetka.ua card parser — product extraction from UIAutomator dumps."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union

from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard


# Rozetka-specific resource-id markers (override from calibration)
ROZETKA_CARD_MARKERS = ("item_card", "product_card", "goods_card", "com.rozetka:id/productView")


class RozetkaCardParser(CardParser):
    """Parses Rozetka product cards from UIAutomator XML dumps.

    Inherits CardParser logic, overriding resource-id markers
    for Rozetka's Android app (com.rozetka).
    """

    CARD_RESOURCE_MARKERS: tuple = ROZETKA_CARD_MARKERS

    def parse(
        self,
        xml_source: Union[str, Path, ET.Element],
        query: str | None = None,
    ) -> list[AdCard]:
        """Parse every product card found in a UI dump."""
        return super().parse(xml_source, query=query)
