---
name: universal-skill-loader-guard
description: Meta-skill that monitors and guards the progressive SKILL.md loader health, auto-discovers new skills, validates progressive disclosure, and triggers self-healing of the skills registry. Use for ПАМЯТЬ, self-evolution, and marketplace integrity.
---
# Universal Skill Loader Guard

## Описание

Этот скил предназначен для...
## Activation
Use when loader health is questioned, after adding new skills, or during marketplace sync.

## Workflow
1. Check loader metadata count vs filesystem SKILL.md files
2. Validate progressive disclosure levels (metadata / full / references)
3. Auto-discover new SKILL.md in core/ and meta/
4. Run validation (YAML frontmatter, <500 lines body, trigger phrases)
5. Trigger re-discovery in loader
6. Log to /run/octopus/skills_loader_health.json
7. If drift > 5 skills → alert + propose skill-creator run
8. Integrate with cas-pack-guard for durable registry backup

## References
- ~/agents/-Octopus/skills/loader/skills_loader.py
- Marketplace index.json
- Per-skill RESEARCH docs

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
- Описание назначения: Meta-skill that monitors and guards the progressive SKILL.md loader health, auto-discovers new skills, validates progressive disclosure, and triggers self-healing of the skills registry. Use for ПАМЯТЬ, self-evolution, and marketplace integrity.
