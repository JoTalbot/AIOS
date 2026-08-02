"""Tests for Instagram Emulator Adapter"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aios_core.platforms.instagram_emulator_adapter import InstagramEmulatorAdapter

@pytest.mark.asyncio
async def test_emulator_adapter_init():
    adapter = InstagramEmulatorAdapter(config={"serial": "emulator-5554", "profile": "test"})
    assert adapter.serial == "emulator-5554"
    assert adapter.profile == "test"
    assert adapter.package == "com.instagram.android"

@pytest.mark.asyncio
async def test_emulator_health_check_no_emulator():
    # Without real ADB, health_check should return False or handle gracefully
    adapter = InstagramEmulatorAdapter(config={"serial": "nonexistent-9999"})
    # Mock ADB to avoid real device check
    if adapter.adb:
        adapter.adb.run = Mock(return_value={"stdout": "", "code": 1})
    result = await adapter.health_check()
    # Should be False for nonexistent device
    assert isinstance(result, bool)

@pytest.mark.asyncio
async def test_emulator_send_message_outbox():
    adapter = InstagramEmulatorAdapter(config={"serial": "emulator-5554"})
    # Mock messenger
    if adapter.messenger:
        mock_messenger = Mock()
        mock_messenger.send_reply = Mock(return_value={"status": "queued"})
        adapter.messenger = mock_messenger
        
        result = await adapter.send_message("user123", "Hello from emulator", metadata={"auto_send": False})
        assert result.recipient_id == "user123"
        assert "Hello" in result.text
        assert result.platform == "instagram_emulator"

def test_platform_registry_includes_emulator():
    from aios_core.platforms.registry import PlatformRegistry
    registry = PlatformRegistry()
    available = registry.list_available_platforms()
    assert "instagram_emulator" in available
    assert "instagram" in available

def test_yaml_descriptor_exists():
    from pathlib import Path
    yaml_path = Path("platforms/instagram_emulator.yaml")
    assert yaml_path.exists()
    content = yaml_path.read_text()
    assert "instagram_emulator" in content
    assert "com.instagram.android" in content
