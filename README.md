# AIOS
Self-evolving distributed operating system for application intelligence, automated testing, API generation, skill evolution and collective learning. Powered by Octopus Runtime.

## Repository layout

- `aios_core/` — Executable layer (Python). 12 core modules (`constitution_engine`, `approval_manager`, `memory_manager`, etc.) plus the full set of AIOS v2.1.1 engine/manager modules merged from `AIOS-Constitution (2).zip`, including `tests/` and config schemas (`rules.json`, `audit_log_schema.json`).
- `constitution/` — Constitutional texts. `ARTICLE_I_SUPREME_PRINCIPLE.md`, `core_principles.md`, and `books/` (BOOK-*/ARTICLE-* of the AIOS Constitution v2.1.1, books II–XXXV plus continuation articles LXXI–CIV).
- `docs/` — Architecture, agent, memory, testing and application docs. `docs/constitution/` holds articles I–LXVII; `docs/executable_layer/` holds the AIOS v2.1.1 layer manifests; `docs/aios_v6/` holds the AIOS v6 / v6.1 "Global Federation" spec (from `AIOS.zip`); `docs/aios_archive_2026/` holds the comprehensive 2026 architecture archive — 127 layer docs across Autonomy, Communication, Compute, Constitution, Deployment, Execution, Federation, Governance, Identity/Trust, Intelligence, Knowledge, Memory, Monitoring, Observability, QA, Roadmaps, Security, Storage and Testing (from `AIOS_Archive_2026.zip`).
- `policies/` — YAML policy definitions (evolution, federation, security and the full set of layer policies from the archive).
- `tests/`, `tools/` — test suite and helper scripts.

## Merged from `AIOS-Constitution (2).zip`
The archive (AIOS Constitution v2.1.1) was integrated: its `Executable-Layer/*.py` modules and `*.yaml` policies were added into `aios_core/` and `policies/` respectively (the repository's original, richer `aios_core` modules were kept), its constitution `BOOK-*`/`ARTICLE-*` files were placed under `constitution/books/`, and its layer documentation manifests were placed under `docs/executable_layer/`.
