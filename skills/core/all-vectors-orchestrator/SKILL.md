---
name: all-vectors-orchestrator
version: 1.0
description: Координация развития Octopus по всем векторам: память, жить, упрощать, сосуществовать, размножаться, развиваться, учиться, меняться.
triggers: [all_vectors_cycle, autonomous_strategy, roadmap_update]
dependencies: [skill-health-monitor, skill-notification, skill-evolution]
llm_required: false
mcp_tools: []
---
# All Vectors Orchestrator

## Описание
Навык безопасно собирает состояние всех стратегических векторов Octopus, формирует score/roadmap и запускает только bounded read-only проверки. Он не отправляет Telegram напрямую, не создаёт платные ресурсы и не выполняет destructive actions без consent gate.

## Алгоритм
1. Собрать факты: health, skills index, telegram drift guard, disk/load/memory, Docker, public endpoints, recent reports/experience.
2. Рассчитать score по векторам: ПАМЯТЬ, ЖИТЬ, УПРОЩАТЬ, СОСУЩЕСТВОВАТЬ, РАЗМНОЖАТЬСЯ, РАЗВИВАТЬСЯ, УЧИТЬСЯ, МЕНЯТЬСЯ.
3. Для каждого вектора записать evidence и следующий bounded step.
4. Сформировать JSON/Markdown отчёты в `reports/` и обновить `roadmap/ALL_VECTORS_STATUS.md`.
5. При `--apply` запустить только read-only guard-проверки и записать `logs/all_vectors_journal.jsonl`.
6. При `--ai` разрешён один bounded skill-evolution proposal через локальный Ollama/Qwen; без прямого Telegram и без платных ресурсов.
7. Любые risky/destructive/cloud действия превращаются только в proposal/rollback, но не выполняются автоматически.

## Контроль и развитие
- Runtime: `code/run.py --apply`.
- Contract tests: `tests/test_contract.py`.
- Systemd: `octopus-all-vectors-dev.timer` (bounded, no direct Telegram).
- Главная метрика: average vector score и отсутствие critical drift.
