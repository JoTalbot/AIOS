---
name: graphrag-exact-citations
description: Этот скил предназначен для...
---

# SKILL: graphrag-exact-citations

## Описание

Этот скил предназначен для...

**Category:** core / memory / RAG
**Status:** ACTIVE

## Purpose
Read-only GraphRAG search API returning auditable provenance for every result: exact source path, indexed SHA256, source size/mtime, excerpt and correlated trace ID.

## Contract
- Endpoint: `GET /search?q=...&limit=...&trace_id=...` on loopback port 9760.
- `citation_contract=exact_source_path+indexed_sha256`.
- Query length capped at 500; result limit capped at 50.
- No writes and no secret indexing.
- MCP `graphrag/search` forwards the same `trace_id`.

## Verification
1. Search returns at least one result for a known query.
2. Every result has `citation.source_path` and 64-hex `source_sha256`.
3. For a live small source, `storage/proof` reads the whole file and its SHA256 matches the indexed citation hash.
4. Services remain loopback-only with `NRestarts=0`.

## Алгоритм
1. Принять bounded query и limit.
2. Выполнить только loopback read-only `/search`.
3. Проверить наличие exact source path и 64-hex indexed SHA256 у каждого результата.
4. Сохранить/передать trace ID без изменения.
5. При отсутствии provenance вернуть fail-closed.

## Runtime
`python3 code/run.py --query Octopus --limit 3 --json`

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
