"""AI agent edge."""
from aios_core.ai_agent import AIAgent
def test_act(): r=AIAgent("1","Bot").act("test"); assert r["status"]=="executed"
def test_learn(): a=AIAgent("2","L"); a.learn({"x":1}); assert a.stats()["experiences"]==1
