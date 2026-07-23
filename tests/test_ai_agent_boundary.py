"""ai_agent boundary test."""
from aios_core.ai_agent import AIAgent

def test_agent_id(): a = AIAgent("id1", "Bot"); assert a.id == "id1"
