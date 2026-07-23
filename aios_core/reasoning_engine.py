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
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ReasoningEngine:
    """Builds explainable reasoning chains.

    v3.0.0: Multi-step chains with memory/knowledge integration.
    """

    def __init__(self, db: Optional[Database] = None, memory=None, knowledge=None):
        self.db = db
        self.memory = memory  # MemoryManager instance
        self.knowledge = knowledge  # KnowledgeGraph instance
        self._chains: list[ReasoningChain] = []
        self._forward_chains: list[dict] = []
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
        chain.steps.append(
            ReasoningStep(
                step_type="premise",
                content=premise_content,
                confidence=1.0,
                sources=["user_input"],
            )
        )

        # Step 2: Evidence gathering
        evidence_sources: list[str] = []

        if use_memory and self.memory:
            memories = self.memory.search(query=question, limit=5)
            if memories:
                for m in memories[:3]:
                    evidence_sources.append(f"memory:{m['id']}")
                chain.steps.append(
                    ReasoningStep(
                        step_type="evidence",
                        content=f"Found {len(memories)} relevant memories",
                        confidence=0.7,
                        sources=list(evidence_sources),
                        metadata={"memory_count": len(memories)},
                    )
                )

        if use_knowledge and self.knowledge:
            # Extract all meaningful words from the question and search for each
            words = [w for w in question.split() if len(w) > 2]  # skip short words
            kg_nodes_found = []
            for word in words[:5]:  # limit to 5 words
                nodes = self.knowledge.find_nodes(label=word, limit=3)
                kg_nodes_found.extend(nodes)
            # Deduplicate by id
            seen_ids: set[str] = set()
            unique_nodes = []
            for n in kg_nodes_found:
                if n["id"] not in seen_ids:
                    seen_ids.add(n["id"])
                    unique_nodes.append(n)
            if unique_nodes:
                for n in unique_nodes[:3]:
                    evidence_sources.append(f"knowledge:{n['id']}")
                chain.steps.append(
                    ReasoningStep(
                        step_type="evidence",
                        content=f"Found {len(unique_nodes)} related knowledge nodes",
                        confidence=0.7,
                        sources=[f"knowledge:{n['id']}" for n in unique_nodes[:3]],
                        metadata={"node_count": len(unique_nodes)},
                    )
                )

        # Step 3: Inference
        has_evidence = any(s.step_type == "evidence" for s in chain.steps)
        inference_conf = 0.6 + (0.2 if has_evidence else 0.0)
        chain.steps.append(
            ReasoningStep(
                step_type="inference",
                content=f"Based on {'evidence and ' if has_evidence else ''}premises, reasoning proceeds with {len(chain.steps)} contextual inputs",
                confidence=inference_conf,
                sources=list(evidence_sources),
            )
        )

        # Step 4: Conclusion
        chain.overall_confidence = self._calculate_chain_confidence(chain.steps)
        chain.conclusion = f"Reasoning complete. Confidence: {chain.overall_confidence:.2f} based on {len(chain.steps)} steps."
        chain.steps.append(
            ReasoningStep(
                step_type="conclusion",
                content=chain.conclusion,
                confidence=chain.overall_confidence,
                sources=list(evidence_sources),
            )
        )

        # Persist
        self._chains.append(chain)
        if self.db and self.memory:
            self.memory.store(
                content={
                    "type": "reasoning_chain",
                    "question": question,
                    "steps": [
                        {
                            "type": s.step_type,
                            "content": s.content,
                            "confidence": s.confidence,
                        }
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

    # ------------------------------------------------------------------
    # Forward-chaining reasoning over the Knowledge Graph
    # ------------------------------------------------------------------

    def forward_chain(self, facts: list[dict], max_depth: int = 5) -> dict:
        """Derive new conclusions from *facts* via the knowledge graph.

        Parameters
        ----------
        facts : list[dict]
            Each dict has keys ``fact``, ``confidence`` (float), ``source`` (str).
        max_depth : int
            Maximum number of inference hops.

        Returns
        -------
        dict
            Same shape as :meth:`_chain_to_dict` output.
        """
        chain_id = self.db.new_id() if self.db else uuid.uuid4().hex[:12]

        chain = ReasoningChain(
            id=chain_id,
            question="forward_chain from "
            + "; ".join(f["fact"][:40] for f in facts[:3]),
        )

        # Seed with the provided facts as premises
        working_facts: list[dict] = []  # {fact, confidence, source, depth}
        for f in facts:
            step = ReasoningStep(
                step_type="premise",
                content=f["fact"],
                confidence=f.get("confidence", 0.8),
                sources=[f.get("source", "unknown")],
            )
            chain.steps.append(step)
            working_facts.append(
                {
                    "fact": f["fact"],
                    "confidence": f.get("confidence", 0.8),
                    "source": f.get("source", "unknown"),
                    "depth": 0,
                }
            )

        # Iteratively derive new facts
        derived_set: set[str] = set()  # track derived fact strings to avoid loops
        iteration = 0
        made_progress = True

        while made_progress and iteration < max_depth:
            made_progress = False
            iteration += 1
            next_facts: list[dict] = []

            for wf in working_facts:
                if wf["depth"] >= max_depth:
                    continue
                if wf["confidence"] < 0.3:
                    continue

                # Query the knowledge graph for rules/nodes related to this fact
                related_nodes: list[dict] = []
                if self.knowledge:
                    try:
                        related_nodes = self.knowledge.find_nodes(
                            label=wf["fact"][:60],
                            limit=5,
                        )
                    except Exception:
                        related_nodes = []

                # Look for "implies" and "causes" relations to derive new facts
                for node in related_nodes:
                    relations: list[dict] = []
                    if self.knowledge:
                        try:
                            relations = self.knowledge.get_relations(
                                node_id=node["id"],
                            )
                        except Exception:
                            relations = []

                    for rel in relations:
                        rel_type = rel.get("type", "")
                        if rel_type not in ("implies", "causes"):
                            continue

                        target_label = rel.get("target_label", rel.get("target", ""))
                        if not target_label or target_label in derived_set:
                            continue

                        # Derivation: confidence decays with depth and relation strength
                        rel_strength = rel.get("weight", rel.get("confidence", 0.7))
                        new_conf = wf["confidence"] * rel_strength * (0.9**iteration)
                        if new_conf < 0.3:
                            continue

                        derived_content = f"{wf['fact']} {rel_type} {target_label}"
                        derived_set.add(derived_content)

                        step = ReasoningStep(
                            step_type="inference",
                            content=derived_content,
                            confidence=round(new_conf, 3),
                            sources=[
                                wf["source"],
                                f"knowledge:{node['id']}",
                                f"relation:{rel.get('id', '')}",
                            ],
                            metadata={
                                "depth": iteration,
                                "relation_type": rel_type,
                                "source_fact": wf["fact"],
                                "target": target_label,
                            },
                        )
                        chain.steps.append(step)
                        next_facts.append(
                            {
                                "fact": target_label,
                                "confidence": round(new_conf, 3),
                                "source": f"inference:{node['id']}",
                                "depth": iteration,
                            }
                        )
                        made_progress = True

            working_facts.extend(next_facts)

        # Build conclusion
        inference_steps = [s for s in chain.steps if s.step_type == "inference"]
        chain.overall_confidence = self._calculate_chain_confidence(chain.steps)
        if inference_steps:
            chain.conclusion = (
                f"Forward chaining derived {len(inference_steps)} new facts "
                f"across {iteration} depth levels. "
                f"Confidence: {chain.overall_confidence:.2f}."
            )
        else:
            chain.conclusion = (
                "Forward chaining completed with no new derivations. "
                f"Confidence: {chain.overall_confidence:.2f}."
            )
        chain.steps.append(
            ReasoningStep(
                step_type="conclusion",
                content=chain.conclusion,
                confidence=chain.overall_confidence,
                sources=[f["source"] for f in facts],
            )
        )

        # Persist
        result = self._chain_to_dict(chain)
        self._forward_chains.append(result)
        self._chains.append(chain)
        return result

    # ------------------------------------------------------------------
    # Explain — enhanced reasoning with multi-word KG search
    # ------------------------------------------------------------------

    def explain(self, question: str, context: dict = None) -> dict:
        """Enhanced reasoning that searches the KG with *all* meaningful words.

        1. Extracts every word longer than 2 characters from *question*.
        2. For each word, queries the knowledge graph.
        3. Finds paths between discovered nodes.
        4. Uses path information to build more specific inferences.
        5. Generates a conclusion that references actual KG nodes/relations.

        Returns the same chain dict format as :meth:`build_chain`.
        """
        chain_id = self.db.new_id() if self.db else uuid.uuid4().hex[:12]
        chain = ReasoningChain(id=chain_id, question=question)

        # Premise
        premise_content = f"Question: {question}"
        if context:
            premise_content += f"\nContext: {context}"
        chain.steps.append(
            ReasoningStep(
                step_type="premise",
                content=premise_content,
                confidence=1.0,
                sources=["user_input"],
            )
        )

        # Extract ALL meaningful words
        words = [w for w in question.split() if len(w) > 2]
        evidence_sources: list[str] = []
        all_nodes: list[dict] = []
        seen_ids: set[str] = set()

        if self.knowledge:
            for word in words[:8]:
                try:
                    nodes = self.knowledge.find_nodes(label=word, limit=5)
                    for n in nodes:
                        if n["id"] not in seen_ids:
                            seen_ids.add(n["id"])
                            all_nodes.append(n)
                except Exception:
                    pass

            if all_nodes:
                for n in all_nodes[:5]:
                    evidence_sources.append(f"knowledge:{n['id']}")
                chain.steps.append(
                    ReasoningStep(
                        step_type="evidence",
                        content=(
                            f"Found {len(all_nodes)} knowledge nodes for "
                            f"{len(words)} search terms: "
                            + ", ".join(n.get("label", n["id"]) for n in all_nodes[:5])
                        ),
                        confidence=0.75,
                        sources=evidence_sources[:5],
                        metadata={
                            "node_count": len(all_nodes),
                            "terms_searched": len(words),
                        },
                    )
                )

                # Find paths between discovered nodes
                paths_found: list[dict] = []
                for i, src_node in enumerate(all_nodes[:4]):
                    for tgt_node in all_nodes[i + 1 : 5]:
                        try:
                            path = self.knowledge.find_path(
                                src_node["id"],
                                tgt_node["id"],
                            )
                            if path:
                                paths_found.append(path)
                        except Exception:
                            pass

                if paths_found:
                    path_descriptions = []
                    for p in paths_found[:3]:
                        path_desc = " -> ".join(
                            step.get("label", step.get("id", "?"))
                            for step in p.get(
                                "nodes", p if isinstance(p, list) else [p]
                            )
                        )
                        path_descriptions.append(path_desc)

                    chain.steps.append(
                        ReasoningStep(
                            step_type="evidence",
                            content=(
                                f"Found {len(paths_found)} paths between nodes: "
                                + "; ".join(path_descriptions)
                            ),
                            confidence=0.7,
                            sources=evidence_sources[:5],
                            metadata={"path_count": len(paths_found)},
                        )
                    )

                    # Build inferences from paths
                    for p in paths_found[:2]:
                        nodes_in_path = p.get("nodes", p if isinstance(p, list) else [])
                        if len(nodes_in_path) >= 2:
                            first_label = nodes_in_path[0].get(
                                "label", nodes_in_path[0].get("id", "?")
                            )
                            last_label = nodes_in_path[-1].get(
                                "label", nodes_in_path[-1].get("id", "?")
                            )
                            chain.steps.append(
                                ReasoningStep(
                                    step_type="inference",
                                    content=(
                                        f"Path from '{first_label}' to '{last_label}' "
                                        f"indicates a relationship relevant to the question"
                                    ),
                                    confidence=0.65,
                                    sources=[
                                        f"knowledge:{nodes_in_path[0].get('id', '')}",
                                        f"knowledge:{nodes_in_path[-1].get('id', '')}",
                                    ],
                                    metadata={"path_length": len(nodes_in_path)},
                                )
                            )

        # Build conclusion that references actual KG nodes found
        chain.overall_confidence = self._calculate_chain_confidence(chain.steps)
        if all_nodes:
            node_labels = [n.get("label", n["id"]) for n in all_nodes[:5]]
            chain.conclusion = (
                f"Based on knowledge graph nodes {node_labels}, "
                f"reasoning identified {len([s for s in chain.steps if s.step_type == 'inference'])} inferences. "
                f"Confidence: {chain.overall_confidence:.2f}."
            )
        else:
            chain.conclusion = (
                "No relevant knowledge graph nodes found for the question. "
                f"Confidence: {chain.overall_confidence:.2f}."
            )
        chain.steps.append(
            ReasoningStep(
                step_type="conclusion",
                content=chain.conclusion,
                confidence=chain.overall_confidence,
                sources=evidence_sources,
            )
        )

        self._chains.append(chain)
        return self._chain_to_dict(chain)

    # ------------------------------------------------------------------
    # Hypothesis evaluation
    # ------------------------------------------------------------------

    def evaluate_hypothesis(
        self,
        hypothesis: str,
        evidence: list[dict] = None,
    ) -> dict:
        """Evaluate a hypothesis against the knowledge graph.

        Searches for supporting and contradicting relations, then returns
        scores and a conclusion.

        Parameters
        ----------
        hypothesis : str
            The hypothesis to evaluate.
        evidence : list[dict] | None
            Optional list of ``{"fact": str, "confidence": float, "source": str}`` dicts.

        Returns
        -------
        dict with keys: hypothesis, supported, support_score,
        contradiction_score, evidence_count, conclusion.
        """
        if evidence is None:
            evidence = []

        support_score = 0.0
        contradiction_score = 0.0
        evidence_count = len(evidence)
        supporting_details: list[str] = []
        contradicting_details: list[str] = []

        # Evaluate provided evidence
        for ev in evidence:
            ev_conf = ev.get("confidence", 0.5)
            ev_fact = ev.get("fact", "")

            # Check if evidence nodes relate to the hypothesis in the KG
            if self.knowledge:
                try:
                    ev_nodes = self.knowledge.find_nodes(label=ev_fact[:60], limit=3)
                    hyp_nodes = self.knowledge.find_nodes(
                        label=hypothesis[:60], limit=3
                    )
                except Exception:
                    ev_nodes = []
                    hyp_nodes = []

                # Check for supporting relations (implies, supports, confirms)
                for en in ev_nodes:
                    for hn in hyp_nodes:
                        try:
                            rels = self.knowledge.get_relations(node_id=en["id"])
                        except Exception:
                            rels = []
                        for r in rels:
                            rel_type = r.get("type", "")
                            if rel_type in (
                                "implies",
                                "supports",
                                "confirms",
                                "causes",
                            ):
                                weight = r.get("weight", r.get("confidence", 0.7))
                                support_score += ev_conf * weight
                                supporting_details.append(
                                    f"{ev_fact} --[{rel_type}]--> {r.get('target_label', '')}"
                                )
                            elif rel_type in ("contradicts", "negates", "refutes"):
                                weight = r.get("weight", r.get("confidence", 0.7))
                                contradiction_score += ev_conf * weight
                                contradicting_details.append(
                                    f"{ev_fact} --[{rel_type}]--> {r.get('target_label', '')}"
                                )
            else:
                # No KG — simple keyword overlap heuristic
                ev_words = set(ev_fact.lower().split())
                hyp_words = set(hypothesis.lower().split())
                overlap = ev_words & hyp_words
                if overlap:
                    support_score += (
                        ev_conf * 0.5 * (len(overlap) / max(len(hyp_words), 1))
                    )
                    supporting_details.append(f"Keyword overlap: {overlap}")

        # Also search KG directly for hypothesis-related relations
        if self.knowledge:
            try:
                hyp_nodes = self.knowledge.find_nodes(label=hypothesis[:60], limit=5)
                for hn in hyp_nodes:
                    try:
                        rels = self.knowledge.get_relations(node_id=hn["id"])
                    except Exception:
                        rels = []
                    for r in rels:
                        rel_type = r.get("type", "")
                        if rel_type in ("implies", "supports", "confirms", "causes"):
                            weight = r.get("weight", r.get("confidence", 0.5))
                            support_score += weight * 0.3
                            supporting_details.append(
                                f"KG relation: {hn.get('label', hn['id'])} --[{rel_type}]--> {r.get('target_label', '')}"
                            )
                        elif rel_type in ("contradicts", "negates", "refutes"):
                            weight = r.get("weight", r.get("confidence", 0.5))
                            contradiction_score += weight * 0.3
                            contradicting_details.append(
                                f"KG relation: {hn.get('label', hn['id'])} --[{rel_type}]--> {r.get('target_label', '')}"
                            )
            except Exception:
                pass

        support_score = round(min(support_score, 1.0), 3)
        contradiction_score = round(min(contradiction_score, 1.0), 3)
        supported = support_score > contradiction_score

        if supported:
            conclusion = (
                f"Hypothesis is supported (support={support_score:.2f}, "
                f"contradiction={contradiction_score:.2f}) based on "
                f"{evidence_count} evidence items and {len(supporting_details)} supporting relations."
            )
        else:
            conclusion = (
                f"Hypothesis is NOT supported (support={support_score:.2f}, "
                f"contradiction={contradiction_score:.2f}) based on "
                f"{evidence_count} evidence items and {len(contradicting_details)} contradicting relations."
            )

        return {
            "hypothesis": hypothesis,
            "supported": supported,
            "support_score": support_score,
            "contradiction_score": contradiction_score,
            "evidence_count": evidence_count,
            "conclusion": conclusion,
        }

    def stats(self) -> dict:
        return {
            "version": "3.0.0",
            "chains_built": len(self._chains),
            "forward_chains": len(self._forward_chains),
            "traces_built": len(self._traces),
            "storage": "sqlite" if self.db else "memory",
        }
