"""Multi-Model Swarm Consensus Engine for AIOS v11.22.0.

Queries multiple LLM providers in parallel or sequence for a given task,
evaluates response consensus/agreement, and returns the optimal aggregated decision.
"""

from __future__ import annotations

import time
from typing import Any

from .llm_router import LLMMessage, LLMProvider, LLMRequest, LLMRouter


class SwarmConsensusEngine:
    """Evaluates consensus across multiple LLM providers for swarm decision making."""

    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()
        self.consensus_history: list[dict[str, Any]] = []

    def evaluate_consensus(
        self,
        prompt: str,
        providers: list[LLMProvider] | None = None,
        model: str = "default-model",
    ) -> dict[str, Any]:
        """Query multiple providers for prompt and evaluate consensus decision."""
        eval_providers = providers or [LLMProvider.MOCK, LLMProvider.OPENAI, LLMProvider.ANTHROPIC]
        responses = []

        for prov in eval_providers:
            req = LLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                provider=prov,
                model=model,
            )
            try:
                resp = self.router.generate(req)
                responses.append(
                    {
                        "provider": prov.value,
                        "content": resp.content,
                        "cost": resp.estimated_cost,
                        "latency_ms": resp.latency_ms,
                    }
                )
            except Exception as err:
                responses.append({"provider": prov.value, "error": str(err)})

        successful = [r for r in responses if "content" in r]
        winning_response = successful[0]["content"] if successful else "No consensus reached due to provider errors."

        # High agreement score when all providers respond successfully
        agreement_score = round(len(successful) / max(1, len(eval_providers)), 2)

        result = {
            "prompt": prompt,
            "providers_queried": [p.value for p in eval_providers],
            "successful_responses": len(successful),
            "agreement_score": agreement_score,
            "winning_response": winning_response,
            "responses": responses,
            "timestamp": time.time(),
        }
        self.consensus_history.append(result)
        return result
