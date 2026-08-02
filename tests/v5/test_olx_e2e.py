import pytest

from aios_core.v5.agents.marketplace.olx_agent import OLXAgent
from aios_core.v5.skills.android.bridge import AndroidBridge


@pytest.mark.asyncio
async def test_olx_android_flow():
    bridge = AndroidBridge()
    bridge.connect()

    agent = OLXAgent(android_skill=bridge)
    result = await agent.execute({"action": "search", "query": "auto glass"})

    assert result["agent"] == "olx_agent"
    assert result["status"] == "planned"
