"""Tests for aios_core/agent_architecture.py"""
from __future__ import annotations
import pytest
from aios_core.agent_architecture import AgentMemory, AdvancedAgent, AgentOrchestrator


class TestAgentMemory:
    def test_create(self):
        mem = AgentMemory()
        assert mem is not None

    def test_add_short_term(self):
        mem = AgentMemory()
        mem.add_short_term({"content": "observation 1", "key": "obs1"})
        mem.add_short_term({"content": "observation 2", "key": "obs2"})

    def test_consolidate(self):
        mem = AgentMemory()
        for i in range(15):
            mem.add_short_term({"content": f"item {i}", "key": f"k{i}"})
        mem.consolidate(threshold=5)

    def test_search_long_term(self):
        mem = AgentMemory()
        mem.add_short_term({"content": "important fact", "key": "imp"})
        mem.consolidate()
        results = mem.search_long_term("important")
        assert isinstance(results, list)

    def test_clear_short_term(self):
        mem = AgentMemory()
        mem.add_short_term({"content": "temp", "key": "temp"})
        mem.clear_short_term()


class TestAdvancedAgent:
    def test_create(self):
        agent = AdvancedAgent(name="test_agent", system_prompt="You are helpful")
        assert agent.name == "test_agent"

    def test_add_tool(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        from aios_core.agent_architecture import Tool
        tool = Tool(name="search", description="Search web", func=lambda q: f"results for {q}")
        agent.add_tool(tool)

    def test_list_tools(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        from aios_core.agent_architecture import Tool
        tool = Tool(name="t1", description="d1", func=lambda: "ok")
        agent.add_tool(tool)
        tools = agent.list_tools()
        assert len(tools) >= 1

    def test_use_tool(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        from aios_core.agent_architecture import Tool
        tool = Tool(name="echo", description="Echo", func=lambda: "ok")
        agent.add_tool(tool)
        result = agent.use_tool("echo")
        assert result is not None

    def test_set_goal(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        agent.set_goal("Deploy v2.0")

    def test_decompose_goal(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        steps = agent.decompose_goal("Build and deploy app")
        assert isinstance(steps, list)

    def test_plan_actions(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        agent.set_goal("Deploy v2.0")
        result = agent.plan_actions()
        assert isinstance(result, (list, dict))

    def test_reflect(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        result = agent.reflect()
        assert isinstance(result, (str, dict))

    def test_stats(self):
        agent = AdvancedAgent(name="a", system_prompt="test")
        s = agent.stats()
        assert isinstance(s, dict)


class TestAgentOrchestrator:
    def test_create(self):
        orch = AgentOrchestrator()
        assert orch is not None

    def test_create_agent(self):
        orch = AgentOrchestrator()
        agent = orch.create_agent(name="worker", system_prompt="Do tasks")
        assert agent is not None

    def test_send_message(self):
        orch = AgentOrchestrator()
        orch.create_agent(name="a1", system_prompt="test")
        orch.create_agent(name="a2", system_prompt="test")
        orch.send_message(from_id="a1", to_id="a2", content="hello")

    def test_broadcast(self):
        orch = AgentOrchestrator()
        orch.create_agent(name="a1", system_prompt="test")
        orch.broadcast(content="announcement")

    def test_stats(self):
        orch = AgentOrchestrator()
        s = orch.stats()
        assert isinstance(s, dict)
