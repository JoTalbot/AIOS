"""Static contract for metadata-only Phone Operations dashboard card."""
from __future__ import annotations
from pathlib import Path


def test_dashboard_contains_safe_phone_operations_card():
    source = (Path(__file__).resolve().parents[1] / "dashboard_v3.py").read_text()
    assert "Центр управления телефоном" in source
    assert "PhoneControlCenter" in source
    assert "Координаты" not in source
