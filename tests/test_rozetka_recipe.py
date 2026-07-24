"""Tests for Rozetka calibration recipe."""

import pytest
from aios_core.platforms import calibration_recipe


class TestRozetkaCalibrationRecipe:
    """Rozetka uses 'ecommerce' kind — cards + detail + messenger + navigation."""

    def test_recipe_ecommerce_kind(self):
        recipe = calibration_recipe("rozetka", "com.rozetka", kind="ecommerce")
        assert recipe["ready"] is False
        assert "cards" in recipe["missing"]
        assert "detail" in recipe["missing"]
        assert "messenger" in recipe["missing"]
        assert "navigation" in recipe["missing"]
        calibrate = next(s for s in recipe["steps"] if s["action"] == "calibrate")
        assert "--dump" in calibrate["command"]
        assert "--detail" in calibrate["command"]
        assert "--messages" in calibrate["command"]
        assert "--navigation" in calibrate["command"]

    def test_recipe_ecommerce_partial_hints(self):
        recipe = calibration_recipe(
            "rozetka", "com.rozetka", kind="ecommerce",
            have_hints={"cards": {"card_markers": [{"resource_id": "x"}]}},
        )
        assert "cards" not in recipe["missing"]
        assert "detail" in recipe["missing"]
        assert "messenger" in recipe["missing"]
        assert "navigation" in recipe["missing"]

    def test_recipe_ecommerce_ready_when_all_hints(self):
        done = calibration_recipe(
            "rozetka", "com.rozetka", kind="ecommerce",
            have_hints={
                "cards": {"card_markers": [{"resource_id": "x:id/card"}]},
                "detail": {"seller_markers": [{"resource_id": "x:id/seller"}]},
                "messenger": {"bubble_markers": [{"resource_id": "x:id/row"}]},
                "navigation": {"reels_tab": {"rid_markers": ["x:id/nav"]}},
            },
        )
        assert done["ready"] is True
        assert done["missing"] == []

    def test_recipe_marketplace_kind_still_works(self):
        """marketplace kind includes cards, detail, messenger (no navigation)."""
        recipe = calibration_recipe("rozetka", "com.rozetka", kind="marketplace")
        assert "cards" in recipe["missing"]
        assert "detail" in recipe["missing"]
        assert "messenger" in recipe["missing"]

    def test_recipe_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            calibration_recipe("rozetka", "com.rozetka", kind="everything")
