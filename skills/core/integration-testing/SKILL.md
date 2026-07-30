---
name: integration-testing
version: 1.0
description: Комплексный набор интеграционных тестов для всех компонентов Octopus
triggers: [test_suite, release_check]
dependencies: []
llm_required: false
mcp_tools: []
---

# SKILL: integration-testing
**Category:** core
**Status:** ACTIVE (on-demand)
**Created:** 2026-06-20 (Batch #91)
**Path:** /opt/octopus-integration-test.py
**Results:** /var/lib/octopus/integration-tests/test_results.json

## Description
Comprehensive integration test suite for all Octopus components.
Tests 14 components: forecaster, DNA, reclaimer, self-mod, BFT, discovery,
reputation, barter, voting, reasoning, collab, skill-factory, evolution, geo-routing.

## Commands
- Run all tests: `python3 /opt/octopus-integration-test.py`
- View results: `cat /var/lib/octopus/integration-tests/test_results.json | jq`

## Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-отчёт: статус, найденные факты, риски, рекомендации, следующий bounded-шаг.
5. Если требуется изменение системы — записать proposal/rollback в logs/reports и ждать consent gate либо выполнения автономным агентом в bounded-режиме.
6. Для Telegram: прямые push-уведомления запрещены, кроме `skill-notification` и отчётов автономного агента.
7. Для AWS/платных ресурсов: только аудит; создание/включение ресурсов запрещено без явной команды человека.

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage и дописывает AI-предложения в `references/`.
- Развитие через ИИ: локальный Ollama/Qwen генерирует bounded improvement proposal; автоприменяются только безопасные структурные улучшения (алгоритм, тест, runtime wrapper).
- Описание назначения: Операционный навык Octopus: integration-testing.

## Release safety verifier (2026-07-11)
`code/release_verify.py` performs a bounded read-only release gate for current reliability/security waves: source existence+SHA256, Python compile, targeted systemd verification, active/NRestarts state, nginx validation and canonical config equality, three runtime guards, local/gateway/external auth contracts, and absence of inline Cloudflare token. It emits a correlated trace ID and never emits credential values.

Command:
`python3 code/release_verify.py --json --output /mnt/agents/-Octopus/reports/<stamp>_release_safety_manifest.json`
