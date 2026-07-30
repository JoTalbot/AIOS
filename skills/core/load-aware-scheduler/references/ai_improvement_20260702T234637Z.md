# AI improvement proposal — load-aware-scheduler

Model: qwen2.5:1.5b
Date: 2026-07-02T23:46:37.853191+00:00

### Назначение

**Критерии принятия решения:**
- Текущая загрузка CPU/RAM/GPU на нодах
- Уже запущенные инструменты (чтобы не дублировать)
- "Специализация" ноды (кто уже хорошо справляется с audio / vector / etc.)
- Стоимость ноды (free-tier приоритет)
- Latency до данных (для RAG/CAS)
- Consent и политика ноды

### Пример
**Нужно запустить whisper-worker**
- выбирает 2 ноды с наименьшей загрузкой + уже имеющие whisper dependencies.

### Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-
