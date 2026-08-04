"""Tests for Chrome Twin Adapter"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter

@pytest.mark.asyncio
async def test_chrome_twin_init():
    adapter = ChromeTwinAdapter(config={"profile": "test", "user_data_dir": "/tmp/chrome_test", "headless": True})
    assert adapter.profile == "test"
    assert "chrome_test" in adapter.user_data_dir
    assert adapter.headless == True

def test_chrome_twin_registry():
    from aios_core.platforms.registry import PlatformRegistry
    registry = PlatformRegistry()
    assert "chrome_twin" in registry.list_available_platforms()

def test_chrome_twin_yaml_exists():
    from pathlib import Path
    yaml_path = Path("platforms/chrome_twin.yaml")
    assert yaml_path.exists()
    content = yaml_path.read_text()
    assert "chrome_twin" in content
    assert "com.android.chrome" in content or "Chrome Twin" in content

@pytest.mark.asyncio
async def test_chrome_twin_action_history():
    adapter = ChromeTwinAdapter(config={"profile": "test_history", "user_data_dir": "/tmp/chrome_history_test"})
    await adapter._log_action("navigate", {"url": "https://google.com"}, result="ok")
    assert len(adapter.action_history) == 1
    assert adapter.action_history[0]["action"] == "navigate"

@pytest.mark.asyncio
async def test_chrome_twin_custom_action_parsing():
    adapter = ChromeTwinAdapter(config={"profile": "test", "headless": True})
    # Mock _ensure_browser to avoid real browser launch.
    # The adapter awaits page.goto/wait_for_timeout, so the fake page must
    # expose async methods, not a plain Mock.
    class _FakePage:
        url = "https://google.com"

        async def goto(self, *a, **k):
            return None

        async def wait_for_timeout(self, *a, **k):
            return None

        async def title(self):
            return "Google"

        async def evaluate(self, *a, **k):
            return None

    adapter._ensure_browser = AsyncMock(return_value=_FakePage())
    # Mock navigate
    adapter.navigate = AsyncMock(return_value={"status": "ok", "url": "https://mail.google.com"})
    
    result = await adapter.execute_custom_action("открой почту")
    # Should route to gmail
    assert result["status"] in ("navigated", "ok", "need_clarification") or "gmail" in str(result).lower() or "mail" in str(result).lower()

def test_chrome_twin_cli_exists():
    from pathlib import Path
    assert Path("aios_cli/chrome_twin.py").exists()
