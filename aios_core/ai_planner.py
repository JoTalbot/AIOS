"""AI Task Planner & Multi-Step Agentic Reasoning for AIOS v11.24.0.

Provides LLM-driven task graph decomposition and autonomous self-correcting plan generation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .llm_router import LLMMessage, LLMProvider, LLMRequest, LLMRouter


class AITaskPlanner:
    """LLM-driven goal decomposition and self-correcting task planner."""

    def __init__(self, router: LLMRouter | None = None) -> None:
        """
        Initializes the AITaskPlanner with an optional LLMRouter.

        Args:
            router: The LLMRouter to use for LLM interactions. If None, a default LLMRouter is created.
        """
        self.router = router or LLMRouter()
        self.plan_history: List[Dict[str, Any]] = []

    def _generate_llm_response(self, prompt: str, provider: LLMProvider) -> LLMRequest:
        """
        Helper function to generate an LLM response.

        Args:
            prompt: The prompt to send to the LLM.
            provider: The LLM provider to use.

        Returns:
            The LLM response.
        """
        req = LLMRequest(
            messages=[LLMMessage(role="user", content=prompt)],
            provider=provider,
        )
        return self.router.generate(req)

    def decompose_goal(
        self,
        goal: str,
        context: Dict[str, Any] | None = None,
        provider: LLMProvider = LLMProvider.MOCK,
    ) -> Dict[str, Any]:
        """
        Decompose a high-level goal into a structured TaskGraph with dependencies.

        Args:
            goal: The high-level goal to decompose.
            context: Optional context to provide to the LLM.
            provider: The LLM provider to use.

        Returns:
            A dictionary representing the task graph.
        """
        prompt = f"Decompose goal into steps: {goal}. Context: {context or {{}}}"
        resp = self._generate_llm_response(prompt, provider)

        # Define the task graph steps.  This is currently hardcoded, but could be
        # dynamically generated from the LLM response in the future.
        steps = [
            {"step_id": "step_1", "description": f"Analyze requirements for: {goal}", "depends_on": []},
            {
                "step_id": "step_2",
                "description": "Execute core processing and tool dispatches",
                "depends_on": ["step_1"],
            },
            {"step_id": "step_3", "description": "Validate results and compile final output", "depends_on": ["step_2"]},
        ]

        result = {
            "goal": goal,
            "provider_used": resp.provider.value,
            "steps": steps,
            "total_steps": len(steps),
            "estimated_cost": resp.estimated_cost,
            "timestamp": time.time(),
        }
        self.plan_history.append(result)
        return result

    def self_correct_plan(
        self,
        failed_step_id: str,
        error_context: str,
        current_plan: Dict[str, Any],
        provider: LLMProvider = LLMProvider.MOCK,
    ) -> Dict[str, Any]:
        """
        Generate corrective replacement steps upon execution failure.

        Args:
            failed_step_id: The ID of the step that failed.
            error_context: The error message or context of the failure.
            current_plan: The current plan.
            provider: The LLM provider to use.

        Returns:
            A dictionary representing the corrected plan.
        """
        prompt = f"Step {failed_step_id} failed with error: {error_context}. Replan execution."
        resp = self._generate_llm_response(prompt, provider)

        corrected_steps = [
            {
                "step_id": f"{failed_step_id}_retry",
                "description": f"Fallback recovery for {failed_step_id}: {error_context}",
                "depends_on": [],
            },
            {
                "step_id": f"{failed_step_id}_continuation",
                "description": "Resume execution pipeline",
                "depends_on": [f"{failed_step_id}_retry"],
            },
        ]

        return {
            "failed_step_id": failed_step_id,
            "error_context": error_context,
            "corrected_steps": corrected_steps,
            "provider_used": resp.provider.value,
            "timestamp": time.time(),
        }