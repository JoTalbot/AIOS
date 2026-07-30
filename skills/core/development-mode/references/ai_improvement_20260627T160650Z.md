# AI improvement proposal — development-mode

Model: qwen2.5:1.5b
Date: 2026-06-27T16:06:50.618433+00:00

### Улучшение навыка "development-mode"

#### Простое использование
"development mode on"
"включи режим разработки"
"останови все модели и скрипты, которые сейчас не нужны"

#### Реализация
Делегирует работу development-mode-guard + dynamic-tool-orchestrator + script-deployer.

#### Обратный режим
"production mode" или "normal mode" — возвращает систему в полноценное состояние.

#### Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-отчёт: статус, найденные факты, риски, рекомендации, следующий bounded-шаг.
5. Если требуется изменение системы — записать proposal/rollback в logs/reports и ждать consent gate либо выполнения
