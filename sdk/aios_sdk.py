"""AIOS Python SDK v4.2.0 - Official client library

H3.12: Full REST + WS + Marketplace + Android + AI Advisor client
Examples: "your agent in 30 lines" per roadmap.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx


class AIOSClient:
    """High-level async client for AIOS REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # --- Core ---

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/health"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def ready(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/ready"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def stats(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/stats"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def metrics(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/metrics"), headers=self.headers)
            resp.raise_for_status()
            return resp.text

    # --- Tasks / Orchestrator ---

    async def create_task(self, name: str, description: str = "", **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/tasks"),
                json={"name": name, "description": description, **kwargs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_tasks(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/tasks"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_task(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(f"/api/v1/tasks/{task_id}"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def evaluate(self, action: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._url("/api/v1/evaluate"), json=action, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Evolution ---

    async def propose_evolution(self, change: dict, component: str, reason: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/evolution/proposals"),
                json={"change": change, "component": component, "reason": reason},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_proposals(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/evolution/proposals"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Memory ---

    async def memory_store(self, content: dict, category: str = "operational", tags: list[str] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/memory"),
                json={"content": content, "category": category, "tags": tags or []},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def memory_search(self, query: str, category: str = "", limit: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/memory/search"),
                params={"query": query, "category": category, "limit": limit},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Knowledge Graph ---

    async def kg_add_node(self, label: str, node_type: str = "entity", properties: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/kg/nodes"),
                json={"label": label, "type": node_type, "properties": properties or {}},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def kg_query(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/kg/query"), params={"q": query}, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Android / Platforms ---

    async def android_list_devices(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/android/devices"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def android_device_status(self, device_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(f"/api/v1/android/devices/{device_id}"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def apps_list(self, platform: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/apps"), params={"platform": platform}, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def apps_get(self, platform: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(f"/api/v1/apps/{platform}"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Shards / Fleet ---

    async def shards_stats(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/shards/stats"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def shards_jobs(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/shards/jobs"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Marketplace ---

    async def marketplace_search(self, query: str = "", tag: str = "", limit: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/marketplace/search"),
                params={"query": query, "tag": tag, "limit": limit},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def marketplace_publish(self, name: str, description: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/marketplace/publish"),
                json={"name": name, "description": description, **kwargs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def marketplace_plugins(self, platform: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/marketplace/plugins"),
                params={"platform": platform},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- AI Advisor (H3.11) ---

    async def advisor_draft_reply(
        self,
        platform: str,
        original_message: str,
        recipient: str,
        item_context: dict | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/advisor/draft"),
                json={
                    "platform": platform,
                    "original_message": original_message,
                    "recipient": recipient,
                    "item_context": item_context or {},
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def advisor_summarize_inbox(self, platform: str, messages: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/advisor/summarize"),
                json={"platform": platform, "messages": messages},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def advisor_price_advice(self, platform: str, item_id: str, current_price: float) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/advisor/price"),
                params={"platform": platform, "item_id": item_id, "current_price": current_price},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Energy, Substrate & Retention (v11.16–v11.19) ---

    async def get_throttle_config(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/substrate/budget/throttle"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def configure_throttle(self, enabled: bool = True, threshold: float = 0.8) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/substrate/budget/throttle"),
                json={"enabled": enabled, "threshold": threshold},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def auto_tune_policy(self, tasks_sample: list[dict] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"tasks": tasks_sample} if tasks_sample else {}
            resp = await client.post(
                self._url("/api/substrate/policy/autotune"),
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_memory_health(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/memory/health"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def prune_snapshots(self, path: str | None = None, max_age_days: float = 30.0, keep_last: int = 5) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"max_age_days": max_age_days, "keep_last": keep_last}
            if path:
                payload["path"] = path
            resp = await client.post(
                self._url("/api/memory/snapshot/prune"),
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def run_retention_maintenance(
        self,
        keep_last_history: int = 1000,
        keep_last_dispatches: int = 1000,
        keep_last_archive: int = 500,
        older_than_seconds: float = 604800.0,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "confirm": True,
                "keep_last_history": keep_last_history,
                "keep_last_dispatches": keep_last_dispatches,
                "keep_last_archive": keep_last_archive,
                "older_than_seconds": older_than_seconds,
            }
            resp = await client.post(
                self._url("/api/retention/maintenance/run"),
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def run_self_healing(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/substrate/self-healing/run"),
                json={"confirm": True},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- AI Multi-LLM, RAG & Swarm Consensus (v11.22.0) ---

    async def ai_generate(self, prompt: str, provider: str = "mock", model: str = "default-model") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/generate"),
                json={"prompt": prompt, "provider": provider, "model": model},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_augment(self, prompt: str, top_k: int = 3) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/augment"),
                json={"prompt": prompt, "top_k": top_k},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_consensus(self, prompt: str, model: str = "default-model") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/consensus"),
                json={"prompt": prompt, "model": model},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- AI Task Planner, GraphRAG, Distillation, Perception & Swarm Federated (v11.24–v11.30) ---

    async def ai_decompose_goal(self, goal: str, context: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/plan/decompose"),
                json={"goal": goal, "context": context},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_correct_plan(self, failed_step_id: str, error_context: str, current_plan: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/plan/correct"),
                json={
                    "failed_step_id": failed_step_id,
                    "error_context": error_context,
                    "current_plan": current_plan or {},
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_query_graph_rag(self, query: str, top_k: int = 3) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/graph-rag/query"),
                json={"query": query, "top_k": top_k},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_collect_trajectory(
        self, agent_id: str, prompt: str, trajectory: list[dict], score: float = 1.0
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/distillation/collect"),
                json={"agent_id": agent_id, "prompt": prompt, "trajectory": trajectory, "score": score},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_prepare_distillation_dataset(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/distillation/dataset"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_process_visual_ui(self, screenshot: str, query: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/perception/ui"),
                json={"screenshot": screenshot, "query": query},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_aggregate_swarm_insights(self, nodes: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/swarm/federated/aggregate"),
                json={"nodes": nodes},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_optimize_prompt(self, prompt: str, metric: str = "accuracy") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/prompt/optimize"),
                json={"prompt": prompt, "metric": metric},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Next-Gen Neural Memory, Causal AI, Swarm Auto-Scale & Privacy Vault (v11.31–v11.35) ---

    async def ai_consolidate_neural_memory(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/memory/consolidate-neural"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_evaluate_what_if(self, action: dict, alternatives: list[dict] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/causal/what-if"),
                json={"action": action, "alternatives": alternatives},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_autoscale_swarm(self, pending_tasks: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/swarm/autoscale"),
                json={"pending_tasks": pending_tasks},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_mask_privacy_payload(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/privacy/mask"),
                json={"payload": payload},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Frontier AI Code Synthesis, Vision RPA Grounding, Quantum AI & Planetary Sync (v11.36–v11.40) ---

    async def ai_synthesize_patch(self, error_log: str, source_code: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/code/synthesize-patch"),
                json={"error_log": error_log, "source_code": source_code},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_ground_rpa_action(self, action_description: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/perception/ground-action"),
                json={"action_description": action_description},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_quantum_optimize_weights(self, weights: list[float]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/quantum/optimize-weights"),
                json={"weights": weights},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_planetary_sync(self, node_states: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/planetary/sync"),
                json={"node_states": node_states},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Singularity Architecture Grand Nexus Suite (v11.51–v11.70) ---

    async def ai_get_singularity_status(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/ai/singularity/status"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Omnipresent Architecture Grand Nexus Suite (v11.71–v12.0.0) ---

    async def ai_get_omnipresent_status(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/ai/omnipresent/status"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Grand Epoch Architecture Nexus Suite (v12.1–v13.0.0) ---

    async def ai_get_grand_epoch_status(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/ai/grand-epoch/status"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Universal Singularity Architecture Suite (v13.1–v14.0.0) ---

    async def ai_get_universal_status(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/ai/universal/status"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Sovereign AI Neuromorphic, Formal Verification, Blockchain & Multi-Species Ethics (v11.41–v11.45) ---

    async def ai_process_spiking_events(self, spikes: list[float], threshold: float = 0.5) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/neuromorphic/process-spikes"),
                json={"spikes": spikes, "threshold": threshold},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_prove_invariant(self, action_code: str, invariant: str = "no_unauthorized_state_mutation") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/formal/prove-invariant"),
                json={"action_code": action_code, "invariant": invariant},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_record_blockchain_proof(self, state_hash: str, signature: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/blockchain/record-proof"),
                json={"state_hash": state_hash, "signature": signature},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_evaluate_alignment(self, intent: str, action_plan: list[dict] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/ethics/evaluate-alignment"),
                json={"intent": intent, "action_plan": action_plan or []},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Cognitive Fabric Cyber-Defense, DNA Code Mutation, Category Theory & Alignment (v11.46–v11.50) ---

    async def ai_evaluate_cyber_defense(self, activity_logs: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/swarm/cyber-defense"),
                json={"activity_logs": activity_logs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_mutate_genome_code(self, genome_code: str, mutation_rate: float = 0.05) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/dna/mutate"),
                json={"genome_code": genome_code, "mutation_rate": mutation_rate},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_map_category_morphisms(self, category_a: list[str], category_b: list[str]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/category/map-morphisms"),
                json={"category_a": category_a, "category_b": category_b},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def ai_evaluate_model_alignment(self, prompts: list[str], outputs: list[str]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/ai/alignment/auto-evaluate"),
                json={"prompts": prompts, "outputs": outputs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- AI Governance, Safety Guard & Compliance Audit (v11.23.0) ---

    async def evaluate_action_safety(self, action: dict, tenant_id: str | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/governance/guard/evaluate"),
                json={"action": action, "tenant_id": tenant_id},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def run_safety_audit(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/governance/audit/run"),
                json={"confirm": True},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_compliance_score(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/governance/compliance/score"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- WebSocket helpers ---

    async def watch_events(self, on_event: Callable[[dict], None], channels: list[str] | None = None):
        """Watch events via WebSocket."""
        try:
            import websockets

            uri = self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/events"
            async with websockets.connect(uri, extra_headers=self.headers) as ws:
                if channels:
                    await ws.send(json.dumps({"subscribe": channels}))
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        on_event(data)
                    except Exception:
                        on_event({"raw": msg})
        except ImportError:
            raise RuntimeError("websockets package required for watch_events") from None


# Synchronous wrapper with all methods mirrored
class AIOSClientSync:
    """Sync wrapper - use in scripts without asyncio."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None):
        self._async = AIOSClient(base_url, api_key)
        self.base_url = self._async.base_url

    def _run(self, coro):
        return asyncio.run(coro)

    # Core
    def health(self):
        return self._run(self._async.health())

    def ready(self):
        return self._run(self._async.ready())

    def stats(self):
        return self._run(self._async.stats())

    def metrics(self):
        return self._run(self._async.metrics())

    # Tasks
    def create_task(self, *a, **kw):
        return self._run(self._async.create_task(*a, **kw))

    def list_tasks(self):
        return self._run(self._async.list_tasks())

    def get_task(self, task_id: str):
        return self._run(self._async.get_task(task_id))

    def evaluate(self, action: dict):
        return self._run(self._async.evaluate(action))

    # Evolution
    def propose_evolution(self, *a, **kw):
        return self._run(self._async.propose_evolution(*a, **kw))

    def list_proposals(self):
        return self._run(self._async.list_proposals())

    # Memory
    def memory_store(self, *a, **kw):
        return self._run(self._async.memory_store(*a, **kw))

    def memory_search(self, *a, **kw):
        return self._run(self._async.memory_search(*a, **kw))

    # KG
    def kg_add_node(self, *a, **kw):
        return self._run(self._async.kg_add_node(*a, **kw))

    def kg_query(self, query: str):
        return self._run(self._async.kg_query(query))

    # Android
    def android_list_devices(self):
        return self._run(self._async.android_list_devices())

    def android_device_status(self, device_id: str):
        return self._run(self._async.android_device_status(device_id))

    def apps_list(self, platform: str = ""):
        return self._run(self._async.apps_list(platform))

    def apps_get(self, platform: str):
        return self._run(self._async.apps_get(platform))

    # Shards
    def shards_stats(self):
        return self._run(self._async.shards_stats())

    def shards_jobs(self):
        return self._run(self._async.shards_jobs())

    # Marketplace
    def marketplace_search(self, *a, **kw):
        return self._run(self._async.marketplace_search(*a, **kw))

    def marketplace_publish(self, *a, **kw):
        return self._run(self._async.marketplace_publish(*a, **kw))

    def marketplace_plugins(self, *a, **kw):
        return self._run(self._async.marketplace_plugins(*a, **kw))

    # Advisor
    def advisor_draft_reply(self, *a, **kw):
        return self._run(self._async.advisor_draft_reply(*a, **kw))

    def advisor_summarize_inbox(self, *a, **kw):
        return self._run(self._async.advisor_summarize_inbox(*a, **kw))

    def advisor_price_advice(self, *a, **kw):
        return self._run(self._async.advisor_price_advice(*a, **kw))

    # Energy, Substrate & Retention (v11.16–v11.19)
    def get_throttle_config(self, *a, **kw):
        return self._run(self._async.get_throttle_config(*a, **kw))

    def configure_throttle(self, *a, **kw):
        return self._run(self._async.configure_throttle(*a, **kw))

    def auto_tune_policy(self, *a, **kw):
        return self._run(self._async.auto_tune_policy(*a, **kw))

    def get_memory_health(self, *a, **kw):
        return self._run(self._async.get_memory_health(*a, **kw))

    def prune_snapshots(self, *a, **kw):
        return self._run(self._async.prune_snapshots(*a, **kw))

    def run_retention_maintenance(self, *a, **kw):
        return self._run(self._async.run_retention_maintenance(*a, **kw))

    def run_self_healing(self, *a, **kw):
        return self._run(self._async.run_self_healing(*a, **kw))

    def ai_generate(self, *a, **kw):
        return self._run(self._async.ai_generate(*a, **kw))

    def ai_augment(self, *a, **kw):
        return self._run(self._async.ai_augment(*a, **kw))

    def ai_consensus(self, *a, **kw):
        return self._run(self._async.ai_consensus(*a, **kw))

    def ai_decompose_goal(self, *a, **kw):
        return self._run(self._async.ai_decompose_goal(*a, **kw))

    def ai_correct_plan(self, *a, **kw):
        return self._run(self._async.ai_correct_plan(*a, **kw))

    def ai_query_graph_rag(self, *a, **kw):
        return self._run(self._async.ai_query_graph_rag(*a, **kw))

    def ai_collect_trajectory(self, *a, **kw):
        return self._run(self._async.ai_collect_trajectory(*a, **kw))

    def ai_prepare_distillation_dataset(self, *a, **kw):
        return self._run(self._async.ai_prepare_distillation_dataset(*a, **kw))

    def ai_process_visual_ui(self, *a, **kw):
        return self._run(self._async.ai_process_visual_ui(*a, **kw))

    def ai_aggregate_swarm_insights(self, *a, **kw):
        return self._run(self._async.ai_aggregate_swarm_insights(*a, **kw))

    def ai_optimize_prompt(self, *a, **kw):
        return self._run(self._async.ai_optimize_prompt(*a, **kw))

    def ai_consolidate_neural_memory(self, *a, **kw):
        return self._run(self._async.ai_consolidate_neural_memory(*a, **kw))

    def ai_evaluate_what_if(self, *a, **kw):
        return self._run(self._async.ai_evaluate_what_if(*a, **kw))

    def ai_autoscale_swarm(self, *a, **kw):
        return self._run(self._async.ai_autoscale_swarm(*a, **kw))

    def ai_mask_privacy_payload(self, *a, **kw):
        return self._run(self._async.ai_mask_privacy_payload(*a, **kw))

    def ai_synthesize_patch(self, *a, **kw):
        return self._run(self._async.ai_synthesize_patch(*a, **kw))

    def ai_ground_rpa_action(self, *a, **kw):
        return self._run(self._async.ai_ground_rpa_action(*a, **kw))

    def ai_quantum_optimize_weights(self, *a, **kw):
        return self._run(self._async.ai_quantum_optimize_weights(*a, **kw))

    def ai_planetary_sync(self, *a, **kw):
        return self._run(self._async.ai_planetary_sync(*a, **kw))

    def ai_get_singularity_status(self, *a, **kw):
        return self._run(self._async.ai_get_singularity_status(*a, **kw))

    def ai_get_omnipresent_status(self, *a, **kw):
        return self._run(self._async.ai_get_omnipresent_status(*a, **kw))

    def ai_get_grand_epoch_status(self, *a, **kw):
        return self._run(self._async.ai_get_grand_epoch_status(*a, **kw))

    def ai_get_universal_status(self, *a, **kw):
        return self._run(self._async.ai_get_universal_status(*a, **kw))

    def ai_process_spiking_events(self, *a, **kw):
        return self._run(self._async.ai_process_spiking_events(*a, **kw))

    def ai_prove_invariant(self, *a, **kw):
        return self._run(self._async.ai_prove_invariant(*a, **kw))

    def ai_record_blockchain_proof(self, *a, **kw):
        return self._run(self._async.ai_record_blockchain_proof(*a, **kw))

    def ai_evaluate_alignment(self, *a, **kw):
        return self._run(self._async.ai_evaluate_alignment(*a, **kw))

    def ai_evaluate_cyber_defense(self, *a, **kw):
        return self._run(self._async.ai_evaluate_cyber_defense(*a, **kw))

    def ai_mutate_genome_code(self, *a, **kw):
        return self._run(self._async.ai_mutate_genome_code(*a, **kw))

    def ai_map_category_morphisms(self, *a, **kw):
        return self._run(self._async.ai_map_category_morphisms(*a, **kw))

    def ai_evaluate_model_alignment(self, *a, **kw):
        return self._run(self._async.ai_evaluate_model_alignment(*a, **kw))

    def evaluate_action_safety(self, *a, **kw):
        return self._run(self._async.evaluate_action_safety(*a, **kw))

    def run_safety_audit(self, *a, **kw):
        return self._run(self._async.run_safety_audit(*a, **kw))

    def get_compliance_score(self, *a, **kw):
        return self._run(self._async.get_compliance_score(*a, **kw))


# Example: "agent in 30 lines"
def example_agent():
    """
    Example usage:

    from sdk.aios_sdk import AIOSClientSync

    client = AIOSClientSync("http://localhost:8000", api_key="local-dev")

    print(client.health())
    print(client.stats())

    # Create a task
    task = client.create_task("analyze_trends", "Analyze OLX trends for iPhone")
    print(task)

    # Draft reply via AI Advisor
    draft = client.advisor_draft_reply(
        platform="olx",
        original_message="Какая последняя цена? Торг уместен?",
        recipient="buyer123",
        item_context={"title": "iPhone 13 128GB", "price": 22000}
    )
    print(draft)

    # Search marketplace
    results = client.marketplace_search(query="olx")
    print(results)
    """
