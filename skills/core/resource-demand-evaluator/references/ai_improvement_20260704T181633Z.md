# AI improvement proposal — resource-demand-evaluator

Model: qwen2.5:1.5b
Date: 2026-07-04T18:16:33.343859+00:00

### Назначение

**Текущий Score: 990/1000**

### Улучшения

#### 1. **Контекст проекта и нагрузки пользователей**
   - Оценивание текущего режима проекта (development / production / maintenance / testing).
   - Анализ активности пользователей (TG bot, API запросы).

#### 2. **Плановые задачи и доступные ресурсы**
   - Проверка плановых задач (chaos tests, eternal snapshots, reproduction).
   - Оценка доступных ресурсов на free-tier нодах.

#### 3. **Примеры решений**
   - "Сейчас идёт активная разработка" → demand для тяжёлых моделей = низкий.
   - "Запущен production voice service" → demand для whisper + vector = высокий.
   - "Ночь + низкая активность" → можно выключить часть нод/процессов.

### Выход

**Возвращает demand-map:**
```json
{
  "whisper-worker": "high",
  "ollama-large":
