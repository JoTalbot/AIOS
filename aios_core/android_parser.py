"""AIOS Android UIAutomator Parser (M1) — focused submodule."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple

__all__ = ["UIElement", "SearchResult", "ItemDetails", "UIAutomatorParser"]


@dataclass
class UIElement:
    resource_id: str
    text: str
    class_name: str
    bounds: Tuple[int, int, int, int]
    clickable: bool
    enabled: bool
    package: str
    content_desc: str = ""

    @property
    def center(self) -> Tuple[int, int, int]:
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2, (y2 - y1))

    def matches_text(self, text: str, partial: bool = True) -> bool:
        if not text:
            return False
        return text.lower() in self.text.lower() if partial else text.lower() == self.text.lower()

    def matches_resource(self, resource_id: str) -> bool:
        return self.resource_id == resource_id or self.resource_id.endswith(resource_id)


@dataclass
class SearchResult:
    """Search result item with title, price, location."""
    item_id: str
    title: str
    price: str
    location: str
    bounds: Tuple[int, int, int, int]


@dataclass
class ItemDetails:
    item_id: str
    title: str
    price: float
    seller: str
    description: str
    status: str


class UIAutomatorParser:
    def __init__(self, xml_content: str):
        self.xml_content = xml_content
        self.root = None

    def parse(self) -> None:
        self.root = ET.fromstring(self.xml_content)
        return self.root

    def find_elements_by_resource(self, resource_id: str) -> None:
        result = []
        if self.root is None:
            return result
        for node in self.root.iter("node"):
            node_resource = node.attrib.get("resource-id", "")
            if resource_id in node_resource:
                result.append(self._to_element(node))
        return result

    def find_elements_by_text(self, text: str, partial: bool = True) -> None:
        result = []
        if self.root is None:
            return result
        for node in self.root.iter("node"):
            node_text = node.attrib.get("text", "")
            if partial and text.lower() in node_text.lower():
                result.append(self._to_element(node))
            elif not partial and text.lower() == node_text.lower():
                result.append(self._to_element(node))
        return result

    def find_clickable_elements(self) -> None:
        result = []
        if self.root is None:
            return result
        for node in self.root.iter("node"):
            if node.attrib.get("clickable") == "true" and node.attrib.get("enabled") == "true":
                result.append(self._to_element(node))
        return result

    def find_search_field(self) -> None:
        for rid in (
            "ua.slando:id/search_field",
            "ua.slando:id/search_src_text",
            "android:id/search_src_text",
        ):
            elements = self.find_elements_by_resource(rid)
            if elements:
                return elements[0]
        if self.root is None:
            return None
        for node in self.root.iter("node"):
            if node.attrib.get("class", "") == "android.widget.EditText":
                return self._to_element(node)
        return None

    def find_search_results(self) -> None:
        results = []
        for rid in (
            "ua.slando:id/adListing_adGridCard",
            "ua.slando:id/ad_grid_card",
            "ua.slando:id/card_root",
        ):
            elements = self.find_elements_by_resource(rid)
            if elements:
                for elem in elements:
                    title = price = location = ""
                    if self.root is None:
                        continue
                    for child in self.root.iter("node"):
                        if self._is_child_of(child, elem):
                            ctext = child.attrib.get("text", "")
                            rid_c = child.attrib.get("resource-id", "")
                            if "title" in rid_c.lower() or "name" in rid_c.lower():
                                title = ctext
                            elif "price" in rid_c.lower():
                                price = ctext
                            elif "location" in rid_c.lower() or "city" in rid_c.lower():
                                location = ctext
                    if title:
                        results.append(
                            SearchResult(
                                f"result_{len(results)}",
                                title,
                                price,
                                location,
                                elem.bounds,
                            )
                        )
                break
        return results

    def find_item_details(self) -> None:
        title = price = seller = description = ""
        for node in self._nodes_by_resource_id("ua.slando:id/adTitle"):
            title = node.attrib.get("text", "")
        for node in self._nodes_by_resource_id("ua.slando:id/adPrice"):
            price = node.attrib.get("text", "")
        for node in self._nodes_by_resource_id("ua.slando:id/seller_name"):
            seller = node.attrib.get("text", "")
        for node in self._nodes_by_resource_id("ua.slando:id/adDescription"):
            description = node.attrib.get("text", "")

        if title:
            return ItemDetails(
                item_id="detail",
                title=title,
                price=float(re.sub(r"[^0-9.,]", "", price).replace(",", ".") or "0"),
                seller=seller,
                description=description,
                status="active",
            )
        return None

    def _nodes_by_resource_id(self, resource_id: str):
        if self.root is None:
            return []
        return [
            node
            for node in self.root.iter("node")
            if resource_id in node.attrib.get("resource-id", "")
        ]

    def _to_element(self, node) -> UIElement:
        bounds = self._parse_bounds(node.attrib.get("bounds", "[0,0][0,0]"))
        return UIElement(
            resource_id=node.attrib.get("resource-id", ""),
            text=node.attrib.get("text", ""),
            class_name=node.attrib.get("class", ""),
            bounds=bounds,
            clickable=node.attrib.get("clickable") == "true",
            enabled=node.attrib.get("enabled") == "true",
            package=node.attrib.get("package", ""),
            content_desc=node.attrib.get("content-desc", ""),
        )

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
            )
        return (0, 0, 0, 0)

    def _is_child_of(self, child_node, parent_elem: UIElement) -> bool:
        bounds = self._parse_bounds(child_node.attrib.get("bounds", "[0,0][0,0]"))
        px1, py1, px2, py2 = parent_elem.bounds
        cx1, cy1, cx2, cy2 = bounds
        return cx1 >= px1 and cy1 >= py1 and cx2 <= px2 and cy2 <= py2
