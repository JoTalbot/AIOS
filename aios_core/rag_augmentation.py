"""RAG & Neural Context Augmenter for AIOS v11.22.0.

Automatically enriches agent prompts with semantic context retrieved from
AgentMemorySystem, VectorStore, and KnowledgeGraph.
"""

from __future__ import annotations

import time
from typing import Any


class ContextAugmenter:
    """Enriches agent prompts with relevant memories, vector chunks, and KnowledgeGraph entities."""

    def __init__(
        self,
        memory_system: Any = None,
        vector_store: Any = None,
        knowledge_graph: Any = None,
    ) -> None:
        self.memory_system = memory_system
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.augmentation_history: list[dict[str, Any]] = []

    def augment_prompt(
        self,
        prompt: str,
        top_k: int = 3,
        memory_system: Any = None,
        vector_store: Any = None,
        knowledge_graph: Any = None,
    ) -> dict[str, Any]:
        """Retrieve relevant context and construct an augmented prompt payload."""
        target_mem = memory_system or self.memory_system
        target_vector = vector_store or self.vector_store
        target_kg = knowledge_graph or self.knowledge_graph

        retrieved_memories: list[str] = []
        vector_chunks: list[str] = []
        kg_entities: list[str] = []

        # 1. Search AgentMemorySystem
        if target_mem is not None and hasattr(target_mem, "recall"):
            try:
                mem_res = target_mem.recall(prompt, limit=top_k)
                if isinstance(mem_res, dict) and "memories" in mem_res:
                    for m in mem_res["memories"]:
                        if isinstance(m, dict):
                            retrieved_memories.append(str(m.get("content") or m.get("result", "")))
                        else:
                            retrieved_memories.append(str(getattr(m, "result", getattr(m, "action", ""))))
            except Exception:
                pass

        # 2. Search VectorStore
        if target_vector is not None and hasattr(target_vector, "search"):
            try:
                v_res = target_vector.search(prompt, top_k=top_k)
                if isinstance(v_res, list):
                    for item in v_res:
                        if isinstance(item, tuple):
                            vector_chunks.append(str(item[0]))
                        elif isinstance(item, dict):
                            vector_chunks.append(str(item.get("text", "")))
            except Exception:
                pass

        # 3. Search KnowledgeGraph
        if target_kg is not None and hasattr(target_kg, "search_nodes"):
            try:
                kg_res = target_kg.search_nodes(prompt)
                if isinstance(kg_res, list):
                    kg_entities.extend(
                        f"Entity: {node.get('label', '')} ({node.get('type', '')})" for node in kg_res[:top_k]
                    )
            except Exception:
                pass

        # Construct augmented prompt
        context_blocks = []
        if retrieved_memories:
            context_blocks.append("[Relevant Memories]:\n" + "\n".join(f"- {m}" for m in retrieved_memories if m))
        if vector_chunks:
            context_blocks.append("[Vector Context]:\n" + "\n".join(f"- {c}" for c in vector_chunks if c))
        if kg_entities:
            context_blocks.append("[Knowledge Graph]:\n" + "\n".join(f"- {e}" for e in kg_entities if e))

        context_text = "\n\n".join(context_blocks)
        augmented_prompt = f"{context_text}\n\n[User Prompt]: {prompt}" if context_text else prompt

        result = {
            "original_prompt": prompt,
            "augmented_prompt": augmented_prompt,
            "context_retrieved": bool(context_blocks),
            "retrieved_memories_count": len(retrieved_memories),
            "vector_chunks_count": len(vector_chunks),
            "kg_entities_count": len(kg_entities),
            "timestamp": time.time(),
        }
        self.augmentation_history.append(result)
        return result
