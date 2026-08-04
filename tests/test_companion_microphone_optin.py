"""Static contract: microphone permission is opt-in and capture remains absent."""
from __future__ import annotations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_microphone_permission_is_requested_only_from_companion_ui():
    manifest = (ROOT / "android_companion/app/src/main/AndroidManifest.xml").read_text()
    activity = (ROOT / "android_companion/app/src/main/java/ua/aios/companion/MainActivity.java").read_text()
    service = (ROOT / "android_companion/app/src/main/java/ua/aios/companion/CompanionService.java").read_text()
    assert "android.permission.RECORD_AUDIO" in manifest
    assert "Manifest.permission.RECORD_AUDIO" in activity
    assert "microphone_capture_enabled\", false" in service
    assert "MediaRecorder" not in service
    assert "AudioRecord" not in service
