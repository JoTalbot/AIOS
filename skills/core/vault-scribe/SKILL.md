---
name: vault-scribe
description: Converts transcripts, notes, strategy docs into polished Obsidian Markdown with frontmatter. Use for memory export, eternal logs, people_graph, packstore manifests. Priority ПАМЯТЬ.
---
# Vault Scribe (psenger adapted)

## Описание

Этот скил предназначен для...
## Workflow
1. Read input (transcript / JSON / CAS object)
2. Generate YAML frontmatter (type: memory|person|eternal|log)
3. Use callouts, embeds, wiki-links
4. Write to packstore or /var/lib/octopus/obsidian/
5. Verify SHA + pack_read_guard
## Examples
- Ingest audio transcript → vault note
- Eternal snapshot summary → Obsidian

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
- Описание назначения: Converts transcripts, notes, strategy docs into polished Obsidian Markdown with frontmatter. Use for memory export, eternal logs, people_graph, packstore manifests. Priority ПАМЯТЬ.
