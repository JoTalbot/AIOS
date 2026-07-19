"""AIOS Reasoning Engine v3.0.0

Builds explainable, multi-step reasoning chains integrating
memory recall, knowledge graph traversal, and constitutional context.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Database
    from .memory_manager import MemoryManager
    from .knowledge_graph import KnowledgeGraph


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_type: str  # premise, inference, conclusion, evidence, contradiction
    content: str
    confidence: float = 0.8
    sources: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """A complete reasoning trace with multiple steps."""
    id: str = ""
    question: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReasoningEngine:
    """Builds explainable reasoning chains.

    v3.0.0: Multi-step chains with memory/knowledge integration.
    """

    def __init__(self, db: Optional[Database] = None, memory=None, knowledge=None):
        self.db = db
        self.memory = memory  # MemoryManager instance
        self.knowledge = knowledge  # KnowledgeGraph instance
        self._chains: list[ReasoningChain] = []
        self._traces: list[dict] = []  # Backward compat (was self.traces)

    @property
    def traces(self) -> list[dict]:
        """Backward compat: alias for _traces."""
        return self._traces

    def build_chain(
        self,
        question: str,
        context: Optional[dict] = None,
        use_memory: bool = False,
        use_knowledge: bool = False,
    ) -> dict:
        """Build a reasoning chain for a question.

        Steps:
        1. Extract key terms from question
        2. If use_memory, search memory for relevant context
        3. If use_knowledge, search knowledge graph for related concepts
        4. Build reasoning steps: premises -> inferences -> conclusion
        5. Calculate overall confidence
        6. Persist the chain
        """
        chain_id = self.db.new_id() if self.db else uuid.uuid4().hex[:12]

        chain = ReasoningChain(
            id=chain_id,
            question=question,
        )

        # Step 1: Premise — restate the question with context
        premise_content = f"Question: {question}"
        if context:
            premise_content += f"\nContext: {context}"
        chain.steps.append(ReasoningStep(
            step_type="premise",
            content=premise_content,
            confidence=1.0,
            sources=["user_input"],
        ))

        # Step 2: Evidence gathering
        evidence_sources: list[str] = []

        if use_memory and self.memory:
            memories = self.memory.search(query=question, limit=5)
            if memories:
                for m in memories[:3]:
                    evidence_sources.append(f"memory:{m['id']}")
                chain.steps.append(ReasoningStep(
                    step_type="evidence",
                    content=f"Found {len(memories)} relevant memories",
                    confidence=0.7,
                    sources=list(evidence_sources),
                    metadata={"memory_count": len(memories)},
                ))

        if use_knowledge and self.knowledge:
            # Use the first word of the question for knowledge graph search
            search_term = question.split()[0] if question else ""
            nodes = self.knowledge.find_nodes(label=search_term, limit=5)
            if nodes:
                for n in nodes[:3]:
                    evidence_sources.append(f"knowledge:{n['id']}")
                chain.steps.append(ReasoningStep(
                    step_type="evidence",
                    content=f"Found {len(nodes)} related knowledge nodes",
                    confidence=0.7,
                    sources=[f"knowledge:{n['id']}" for n in nodes[:3]],
                    metadata={"node_count": len(nodes)},
                ))

        # Step 3: Inference
        has_evidence = any(s.step_type == "evidence" for s in chain.steps)
        inference_conf = 0.6 + (0.2 if has_evidence else 0.0)
        chain.steps.append(ReasoningStep(
            step_type="inference",
            content=f"Based on {'evidence and ' if has_evidence else ''}premises, reasoning proceeds with {len(chain.steps)} contextual inputs",
            confidence=inference_conf,
            sources=list(evidence_sources),
        ))

        # Step 4: Conclusion
        chain.overall_confidence = self._calculate_chain_confidence(chain.steps)
        chain.conclusion = f"Reasoning complete. Confidence: {chain.overall_confidence:.2f} based on {len(chain.steps)} steps."
        chain.steps.append(ReasoningStep(
            step_type="conclusion",
            content=chain.conclusion,
            confidence=chain.overall_confidence,
            sources=list(evidence_sources),
        ))

        # Persist
        self._chains.append(chain)
        if self.db and self.memory:
            self.memory.store(
                content={
                    "type": "reasoning_chain",
                    "question": question,
                    "steps": [
                        {"type": s.step_type, "content": s.content, "confidence": s.confidence}
                        for s in chain.steps
                    ],
                    "conclusion": chain.conclusion,
                    "overall_confidence": chain.overall_confidence,
                },
                category="operational",
                tags=["reasoning", "chain"],
                source="reasoning_engine",
            )

        return self._chain_to_dict(chain)

    def _calculate_chain_confidence(self, steps: list[ReasoningStep]) -> float:
        """Calculate overall chain confidence as weighted average."""
        if not steps:
            return 0.0
        # Later steps (conclusions) have more weight
        total_weight = 0.0
        weighted_sum = 0.0
        for i, step in enumerate(steps):
            weight = (i + 1) / len(steps)  # 1/N, 2/N, ..., N/N
            weighted_sum += step.confidence * weight
            total_weight += weight
        return round(weighted_sum / total_weight, 3) if total_weight > 0 else 0.0

    def _chain_to_dict(self, chain: ReasoningChain) -> dict:
        return {
            "id": chain.id,
            "question": chain.question,
            "steps": [
                {
                    "type": s.step_type,
                    "content": s.content,
                    "confidence": s.confidence,
                    "sources": s.sources,
                }
                for s in chain.steps
            ],
            "conclusion": chain.conclusion,
            "overall_confidence": chain.overall_confidence,
            "step_count": len(chain.steps),
            "created_at": chain.created_at,
        }

    # Backward compat
    def reason(self, decision: str, rules: list, sources: list) -> dict:
        trace = {
            "decision": decision,
            "rules_applied": rules,
            "knowledge_sources": sources,
            "confidence": self._calculate_confidence(rules, sources),
        }
        self._traces.append(trace)
        return trace

    def _calculate_confidence(self, rules: list, sources: list) -> float:
        base_confidence = 0.5
        rule_boost = len(rules) * 0.1
        source_boost = len(sources) * 0.15
        return min(0.95, base_confidence + rule_boost + source_boost)

    def last_trace(self) -> dict:
        return self._traces[-1] if self._traces else None

    def stats(self) -> dict:
        return {
            "version": "3.0.0",
            "chains_built": len(self._chains),
            "traces_built": len(self._traces),
            "storage": "sqlite" if self.db else "memory",
        }