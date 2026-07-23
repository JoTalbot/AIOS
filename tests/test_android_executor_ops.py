"""Android executor operations."""
from aios_core.android_execution import UIAutomatorParser, UIElement
def test_element(): e = UIElement("id", "txt", "cls", (0,0,100,100), True, True, "pkg"); assert e.text == "txt"
