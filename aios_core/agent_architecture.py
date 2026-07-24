"""Advanced Agent Architecture for AIOS

Full-featured autonomous agent framework with memory consolidation,
tool chaining, goal decomposition, ReAct-style execution loops,
multi-agent collaboration, self-reflection, and plan revision.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["AdvancedAgent", "AgentMemory", "AgentOrchestrator", "Tool"]


@dataclass
class AgentMemory:
    """Tripartite memory: short-term, long-term, and episodic stores.

    Supports consolidation from short-term → long-term, and episodic
    replay for learning from past experiences.
    """

    short_term: list[dict] = field(default_factory=list)
    long_term: dict = field(default_factory=dict)
    episodic: list[dict] = field(default_factory=list)
    max_short_term: int = 100

    def add_short_term(self, item: dict) -> None:
        """Add item to short-term memory; evict oldest if overflow."""
        self.short_term.append(item)
        if len(self.short_term) > self.max_short_term:
            self.short_term = self.short_term[-self.max_short_term :]

    def consolidate(self, threshold: int = 5) -> int:
        """Consolidate frequently-seen short-term items into long-term.

        Items appearing >= *threshold* times in short-term are promoted
        to long-term.  Returns count of consolidated items.
        """
        freq: dict[str, int] = {}
        for item in self.short_term:
            key = item.get("key", str(item))
            freq[key] = freq.get(key, 0) + 1

        promoted = 0
        for key, count in freq.items():
            if count >= threshold and key not in self.long_term:
                self.long_term[key] = {
                    "frequency": count,
                    "promoted_from": "short_term",
                }
                promoted += 1

        # Remove promoted items from short-term
        promoted_keys = {k for k, c in freq.items() if c >= threshold}
        self.short_term = [
            item
            for item in self.short_term
            if item.get("key", str(item)) not in promoted_keys
        ]
        return promoted

    def add_episodic(self, episode: dict) -> None:
        """Record an episodic experience."""
        self.episodic.append(episode)

    def replay_episodes(self, limit: int = 10) -> list[dict]:
        """Return recent episodic memories."""
        return self.episodic[-limit:]

    def search_long_term(self, query: str) -> list[dict]:
        """Search long-term memory for entries matching *query*."""
        results = []
        for key, value in self.long_term.items():
            if query.lower() in key.lower():
                results.append({"key": key, "value": value})
        return results

    def clear_short_term(self) -> None:
        """Clear short-term memory."""
        self.short_term.clear()


@dataclass
class Tool:
    """An invokable tool that an agent can use."""

    name: str
    description: str
    func: Callable
    category: str = "general"

    def execute(self, *args, **kwargs) -> Any:
        """Run the tool's function."""
        return self.func(*args, **kwargs)


class AdvancedAgent:
    """Full-featured autonomous agent.

    Combines memory, tools, goal-driven planning, ReAct execution,
    self-reflection, and plan revision.
    """

    def __init__(self, name: str, system_prompt: str = ""):
        """Initialize AdvancedAgent."""
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.system_prompt = system_prompt
        self.memory = AgentMemory()
        self.tools: dict[str, Tool] = {}
        self.goals: list[str] = []
        self.plan: list[dict] = []
        self.completed_steps: list[dict] = []
        self.reflections: list[str] = []

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def add_tool(self, tool: Tool) -> None:
        """Register a tool under its name."""
        self.tools[tool.name] = tool

    def remove_tool(self, name: str) -> bool:
        """Remove a registered tool."""
        return self.tools.pop(name, None) is not None

    def list_tools(self) -> list[str]:
        """Return names of available tools."""
        return list(self.tools.keys())

    def use_tool(self, name: str, *args, **kwargs) -> Any:
        """Execute a named tool."""
        tool = self.tools.get(name)
        if tool is None:
            return {"error": f"Tool '{name}' not found"}
        try:
            result = tool.execute(*args, **kwargs)
            self.memory.add_short_term(
                {
                    "key": f"tool_call:{name}",
                    "tool": name,
                    "args": str(args),
                    "result": str(result),
                }
            )
            return result
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Goal management
    # ------------------------------------------------------------------

    def set_goal(self, goal: str) -> None:
        """Append a goal to the agent's goal stack."""
        self.goals.append(goal)

    def decompose_goal(self, goal: str) -> list[str]:
        """Break a goal into sub-goals using heuristics."""
        # Simple decomposition: split by conjunction words
        subgoals: list[str] = []
        parts = (
            goal.replace(" and ", "|")
            .replace(" then ", "|")
            .replace(" after ", "|")
            .split("|")
        )
        for part in parts:
            subgoals.append(part.strip())
        if not subgoals:
            subgoals = [goal]
        self.goals.extend(subgoals)
        return subgoals

    def clear_goals(self) -> None:
        """Remove all goals."""
        self.goals.clear()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan_actions(self) -> list[dict]:
        """Generate a simplified action plan based on goals and tools."""
        self.plan = []
        available_tools = list(self.tools.keys())

        for i, goal in enumerate(self.goals):
            # Choose a tool for each goal if available
            if available_tools:
                tool_name = available_tools[i % len(available_tools)]
                step = {
                    "step": i + 1,
                    "action": "use_tool",
                    "tool": tool_name,
                    "goal": goal,
                }
            else:
                step = {"step": i + 1, "action": "think", "goal": goal}
            self.plan.append(step)

        return self.plan

    def revise_plan(self, feedback: str) -> list[dict]:
        """Revise the plan based on reflection feedback."""
        # Simple revision: add a "think" step after each tool step
        revised: list[dict] = []
        for i, step in enumerate(self.plan):
            revised.append(step)
            if step["action"] == "use_tool":
                revised.append(
                    {
                        "step": i + 1 + len(revised),
                        "action": "think",
                        "goal": f"Review result of {step['tool']}",
                    }
                )
        self.plan = revised
        return self.plan

    # ------------------------------------------------------------------
    # Execution (ReAct-style)
    # ------------------------------------------------------------------

    def execute_step(self, step: dict) -> dict:
        """Execute a single plan step (ReAct: Reason → Act → Observe)."""
        action = step.get("action", "think")
        result: dict[str, Any] = {"status": "completed", "step": step}

        if action == "use_tool":
            tool_name = step.get("tool", "")
            tool_result = self.use_tool(tool_name)
            result["tool_result"] = tool_result
        elif action == "think":
            thought = f"Thinking about: {step.get('goal', 'unknown')}"
            result["thought"] = thought
            self.memory.add_short_term({"key": "thought", "content": thought})
        else:
            result["status"] = "skipped"
            result["reason"] = f"Unknown action: {action}"

        # Record observation
        self.completed_steps.append(result)
        self.memory.add_episodic(
            {
                "step": step,
                "result": result,
                "agent_id": self.id,
            }
        )
        return result

    def execute_plan(self) -> list[dict]:
        """Execute all steps in the current plan sequentially."""
        results: list[dict] = []
        for step in self.plan:
            result = self.execute_step(step)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Self-reflection
    # ------------------------------------------------------------------

    def reflect(self) -> str:
        """Self-reflect on goal progress and completed steps."""
        completed = len(self.completed_steps)
        total = len(self.plan)
        tool_calls = sum(
            1 for s in self.completed_steps if s.get("tool_result") is not None
        )

        progress = completed / max(1, total)
        reflection = f"Reflection: {completed}/{total} steps completed ({progress:.0%}). Tool calls: {tool_calls}."
        self.reflections.append(reflection)
        return reflection

    def auto_reflect_and_revise(self) -> dict[str, Any]:
        """Reflect, then revise the plan if progress is < 50%."""
        reflection = self.reflect()
        progress = len(self.completed_steps) / max(1, len(self.plan))

        revised = None
        if progress < 0.5:
            revised = self.revise_plan(reflection)

        return {
            "reflection": reflection,
            "progress": round(progress, 3),
            "plan_revised": revised is not None,
            "revised_plan": revised,
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return agent summary stats."""
        return {
            "id": self.id,
            "name": self.name,
            "tools": len(self.tools),
            "goals": len(self.goals),
            "plan_steps": len(self.plan),
            "completed_steps": len(self.completed_steps),
            "short_term_items": len(self.memory.short_term),
            "long_term_items": len(self.memory.long_term),
            "episodic_items": len(self.memory.episodic),
            "reflections": len(self.reflections),
        }


class AgentOrchestrator:
    """Manages multiple AdvancedAgent instances with collaboration support.

    Features:
    - Agent creation and registration
    - Inter-agent message passing
    - Task delegation based on tool availability
    - Consensus gathering among agents
    """

    def __init__(self):
        """Initialize AgentOrchestrator."""
        self.agents: dict[str, AdvancedAgent] = {}
        self._messages: list[dict[str, Any]] = []

    def create_agent(self, name: str, system_prompt: str = "") -> AdvancedAgent:
        """Create and register a new agent."""
        agent = AdvancedAgent(name, system_prompt)
        self.agents[agent.id] = agent
        return agent

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the orchestrator."""
        return self.agents.pop(agent_id, None) is not None

    def send_message(
        self, from_id: str, to_id: str, content: str, topic: str = ""
    ) -> dict[str, Any]:
        """Send a message between agents."""
        if from_id not in self.agents or to_id not in self.agents:
            return {"success": False, "error": "Agent not found"}

        msg = {
            "from": from_id,
            "to": to_id,
            "content": content,
            "topic": topic,
        }
        self._messages.append(msg)
        # Deliver to target agent's memory
        self.agents[to_id].memory.add_short_term(
            {
                "key": f"message_from:{from_id}",
                "content": content,
                "topic": topic,
            }
        )
        return {"success": True, "message": msg}

    def delegate_task(self, task: str, required_tool: str = "") -> AdvancedAgent | None:
        """Find and return the best agent for a task based on tool availability."""
        candidates = []
        for agent in self.agents.values():
            if (required_tool and required_tool in agent.tools) or not required_tool:
                candidates.append(agent)

        if not candidates:
            return None

        # Choose agent with fewest current goals (most available)
        return min(candidates, key=lambda a: len(a.goals))

    def gather_consensus(self, question: str) -> dict[str, Any]:
        """Collect reflections from all agents on a question."""
        responses: dict[str, str] = {}
        for agent_id, agent in self.agents.items():
            agent.set_goal(question)
            reflection = agent.reflect()
            responses[agent_id] = reflection

        # Simple majority: check if responses agree
        unique_responses = set(responses.values())
        consensus = len(unique_responses) <= 1

        return {
            "question": question,
            "responses": responses,
            "consensus": consensus,
            "agent_count": len(self.agents),
        }

    def broadcast(self, content: str, topic: str = "") -> int:
        """Broadcast a message to all agents."""
        count = 0
        for agent in self.agents.values():
            agent.memory.add_short_term(
                {
                    "key": f"broadcast:{topic}",
                    "content": content,
                    "topic": topic,
                }
            )
            count += 1
        return count

    def stats(self) -> dict:
        """Return orchestrator statistics."""
        return {
            "agents": len(self.agents),
            "messages_sent": len(self._messages),
            "agent_ids": list(self.agents.keys()),
        }
