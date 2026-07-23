import pytest
from aios_core.ai_agent import AIAgent

@pytest.mark.parametrize("goal", ["search", "analyse", "report", "deploy"])
def test_agent_act(goal):
    a = AIAgent("id1", "Bot")
    r = a.act(goal)
    assert r["status"] == "executed"
    assert goal in r["result"]

@pytest.mark.parametrize("experiences", [0,1,5,10])
def test_learn_count(experiences):
    a = AIAgent("id1", "Bot")
    for i in range(experiences):
        a.learn({"task": i})
    assert a.stats()["experiences"] == experiences
