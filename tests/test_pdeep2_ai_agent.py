"""Parametrized deep: ai_agent."""
import pytest
from aios_core.ai_agent import AIAgent
@pytest.mark.parametrize("goal",["search","analyse","report"])
def test_agent(goal):
    a = AIAgent("id","Bot")
    r = a.act(goal)
    assert r["status"]=="executed"
    assert goal in r["result"]

