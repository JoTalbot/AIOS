"""Integration test for Android RPA Mobile Agent with Multimodal Vision Perception (AIOS v15.0.0)."""

from __future__ import annotations

from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator, AndroidRPAManager
from aios_core.multimodal_perception import MultimodalPerceptionEngine
from aios_core.vision_rpa_grounding import VisionRPAGroundingEngine


def test_android_multimodal_rpa_end_to_end_loop():
    """Test full end-to-end mobile RPA perception & execution loop."""
    # 1. Initialize Android RPA Device Emulator
    rpa_manager = AndroidRPAManager()
    emulator = AndroidRPADeviceEmulator(device_id="emulator-5554")
    assert emulator.device_id == "emulator-5554"

    # 2. Capture screenshot & analyze UI elements via Multimodal Perception
    perception = MultimodalPerceptionEngine()
    ui_analysis = perception.process_visual_ui("simulated_screen_base64_data", query="click login button")

    assert ui_analysis["detected_elements_count"] >= 1
    assert "btn_login" in ui_analysis["suggested_action"]

    # 3. Ground natural language RPA action to UI click coordinates
    grounder = VisionRPAGroundingEngine()
    grounding_res = grounder.ground_action_to_coordinates("click login button")

    assert grounding_res["target_element_id"] == "btn_login"
    click_coords = grounding_res["click_coordinates"]
    assert click_coords == {"x": 150, "y": 225}

    # 4. Execute RPA action on Android emulator
    action_res = emulator.execute_ui_action(
        package_name="ua.slando",
        action_name="search",
        params={"query": "iPhone"},
    )
    assert action_res["package"] == "ua.slando"
    assert action_res["action"] == "search"
    assert action_res["results_count"] == 15

    # 5. Check RPA manager stats
    stats = rpa_manager.stats()
    assert "converted_apps_count" in stats
