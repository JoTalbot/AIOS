"""
AIOS OLX Android Agent

UIAutomator XML parser
"""

import xml.etree.ElementTree as ET
from pathlib import Path


class UIParser:

    def __init__(self, xml_file):
        self.xml_file = Path(xml_file)
        self.root = None

    def load(self) -> None:
        """Execute load."""
        tree = ET.parse(self.xml_file)
        self.root = tree.getroot()
        return self.root

    def find_by_resource(self, resource_id) -> None:
        """Execute find by resource."""
        result = []

        for node in self.root.iter("node"):
            if node.attrib.get("resource-id") == resource_id:
                result.append(node.attrib)

        return result

    def find_text(self) -> None:
        """Execute find text."""
        result = []

        for node in self.root.iter("node"):
            text = node.attrib.get("text")

            if text:
                result.append(text)

        return result


if __name__ == "__main__":

    import sys

    xml_file = "olx_ui.xml"

    if len(sys.argv) > 1:
        xml_file = sys.argv[1]

    parser = UIParser(xml_file)

    parser.load()

    cards = parser.find_by_resource("adListing_adGridCard")

    print("Cards:", len(cards))

    print(parser.find_text())
