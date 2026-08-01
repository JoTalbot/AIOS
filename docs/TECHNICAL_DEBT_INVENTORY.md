# Technical Debt Inventory

Generated automatically. This report is an inventory, **not** a deletion plan. Each item must have tests and an owner before removal or consolidation.

## Versioned core modules

Total: **29**

- `active_inference_v2.py`
- `ai_advisor_v2.py`
- `category_theory_mapper_v2.py`
- `circuit_breaker_v2.py`
- `code_synthesizer_v2.py`
- `goal_decomposer_v2.py`
- `grand_epoch_nexus_v13.py`
- `graph_rag_v3.py`
- `graph_rag_v4.py`
- `infinite_cognition_nexus_v15.py`
- `leader_election_v2.py`
- `llm_fallback_v2.py`
- `mesh_sync_v2.py`
- `multimodal_v3.py`
- `multimodal_v4.py`
- `privacy_vault_v2.py`
- `privacy_vault_v3.py`
- `prompt_tuner_v3.py`
- `prompt_tuner_v4.py`
- `quantum_annealing_v2.py`
- `self_healing_pipeline_v2.py`
- `singularity_universal_nexus_v14.py`
- `swarm_consensus_v2.py`
- `swarm_consensus_v3.py`
- `swarm_federated_v3.py`
- `swarm_federated_v4.py`
- `task_balancer_v2.py`
- `topological_compression_v2.py`
- `zk_vault_v2.py`

## Legacy `/app/` path references

Total Python files: **7**

- `run_telegram_bot.py`
- `seed_dashboard_data.py`
- `octopus_core/server.py`
- `aios_core/dashboard.py`
- `aios_core/llm_balancer.py`
- `aios_core/api/mixins_core.py`
- `tests/test_h2_batch.py`

## Recommended sequence

1. Mark one implementation as canonical for each duplicated subsystem.
2. Add focused contract tests before changing imports.
3. Move unused implementations to an explicitly named `legacy/` area or deprecate them.
4. Remove only after a release cycle with no runtime imports.
5. Keep deployment paths configurable via environment variables; do not hard-code `/app`, `/opt/aios`, or `/root/AIOS`.
