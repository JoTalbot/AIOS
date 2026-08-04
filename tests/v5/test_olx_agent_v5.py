import pytest

from aios_core.v5.agents.marketplace.olx_agent import OLXAgent


@pytest.mark.asyncio
async def test_olx_agent_execute():
    agent = OLXAgent()
    result = await agent.execute({"action": "search"})

    assert result["agent"] == "olx_agent"
    assert result["action"] == "search"
