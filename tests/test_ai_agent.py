"""Tests for AI Agent abstraction."""

from aios_core.ai_agent import AIAgent


def test_agent_act():
    agent = AIAgent(id="agent-1", name="TestBot")
    result = agent.act("search the web")
    assert result["status"] == "executed"
    assert "TestBot" in result["result"]


def test_agent_learn_and_stats():
    agent = AIAgent(id="a2", name="Learner")
    agent.learn({"task": "summarize", "outcome": "ok"})
    agent.learn({"task": "translate", "outcome": "ok"})
    s = agent.stats()
    assert s["experiences"] == 2
    assert s["autonomy"] == 2


def test_agent_default_values():
    agent = AIAgent(id="a3", name="DefaultBot")
    assert agent.autonomy_level == 2
    assert agent.capabilities == []
    assert agent.memory == {}


def test_agent_act_with_context():
    agent = AIAgent(id="a4", name="CtxBot")
    result = agent.act("analyse", context={"lang": "uk"})
    assert result["agent_id"] == "a4"
    assert result["goal"] == "analyse"
