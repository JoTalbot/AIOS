# AIOS v4.2.0-alpha — Детальная Декомпозиция Задач (WBS) и Майлстоуны

**Целевая версия:** `v4.2.0-alpha`  
**Сроки выполнения:** Q1 2027 (12 недель разработки)  
**Базовая версия:** `v4.1.0-alpha` (526 passed tests, 67 constitutional articles verified)

---

## 📅 График Майлстоунов (Milestones Timeline)

```
[Недели 1-3]   Milestone 4.2.1: Advanced ML Intelligence Layer
[Недели 4-6]   Milestone 4.2.2: Production Hardening & OpenTelemetry
[Недели 7-10]  Milestone 4.2.3: Official Web UI (React + Vite + Tailwind)
[Недели 11-12] Milestone 4.2.4: Enterprise PostgreSQL Support & Scale-Out
```

---

## 🗂 Подробная Структура Работ (Work Breakdown Structure - WBS)

### 🚀 Milestone 4.2.1: Advanced ML Intelligence Layer (Недели 1–3) — ✅ Завершено

#### WBS 1.1 — Интеграция Реестра ML Моделей (`model_registry.py`)
- **Задача:** Разработка универсального класса `ModelRegistry` для закрузки, версионирования и локального исполнения ONNX и scikit-learn моделей.
- **Модули:** `aios_core/model_registry.py`, `aios_core/model_serving.py`
- **Критерии приемки:**
  - [x] Поддержка сериализации и верификации SHA256.
  - [x] Метод `predict(model_id, input_data)` со средней задержкой < 10 мс.
  - [x] Версионирование моделей, A/B Traffic Splitting и откат на резервные веса.

#### WBS 1.2 — Детектор Аномалий Выполнения Задач (`anomaly_detection.py`)
- **Задача:** Автономное выявление аномалий в поведении агентов и времени выполнения шагов пайплайна.
- **Модули:** `aios_core/anomaly_detection.py`
- **Критерии приемки:**
  - [x] Алгоритмы Z-Score / IQR для одно- и многомерных метрик.
  - [x] Фиксация аномалий и протоколирование аномальных выбросов.

#### WBS 1.3 — Предиктивная Регулировка Автономии (`predictive_autonomy.py`)
- **Задача:** Прогнозирование вероятности ошибки до отправки задачи на исполнение.
- **Модули:** `aios_core/predictive_autonomy.py`
- **Критерии приемки:**
  - [x] Временное понижение уровня автономии агента при высоком прогнозируемом риске (clamping down to Level 1 / Level 2).

#### WBS 1.4 — Покрытие Тестами ML Слой
- **Файлы тестов:** `tests/test_ml_registry.py` (все 530 тестов пройдены)

---

### 🛡 Milestone 4.2.2: Production Hardening & Observability (Недели 4–6) — ✅ Завершено

#### WBS 2.1 — Интеграция OpenTelemetry & Distributed Tracing
- **Задача:** Внедрение OTLP экспортёра и W3C Trace Context заголовков для сквозной трассировки вызовов.
- **Модули:** `aios_core/telemetry.py`, `aios_core/tracing.py`
- **Критерии приемки:**
  - [x] Поддержка W3C `traceparent` формата (`00-{trace_id}-{span_id}-01`).
  - [x] Автоматическая прокидка контекста спанов и замер задержек.
  - [x] Экспорт метрик (Counters, Gauges, Histograms) в формате Prometheus.

#### WBS 2.2 — Структурированное JSON Логирование
- **Задача:** Перевод всех системных логов на единый JSON-формат с добавлением context trace-id, agent-id, constitutional status.
- **Модули:** `aios_core/logging_config.py`
- **Критерии приемки:**
  - [x] `JSONFormatter` обогащает логи полями `trace_id`, `span_id`, `agent_id`, `constitutional_status`.

#### WBS 2.3 — Backup & Disaster Recovery Engine
- **Задача:** Автоматический механизм горячего снимка состояния (WAL Snapshot) и быстрого восстановления базы при сбое.
- **Модули:** `aios_core/backup_manager.py`
- **Критерии приемки:**
  - [x] Использование горячего `sqlite3.backup` API без блокировки чтения.
  - [x] Валидация SHA256 контрольных сумм при восстановлении `restore_backup()`.
  - [x] Ротация бэкапов и ротация глубин хранения.

#### WBS 2.4 — Набор Нагрузочных и Отказоустойчивых Тестов
- **Файлы тестов:** `tests/test_telemetry.py`, `tests/test_backup_manager.py` (все 535 тестов пройдены)

---

### 💻 Milestone 4.2.3: Official Web UI (React + Vite + Tailwind) (Недели 7–10) — ✅ Завершено

#### WBS 3.1 — Компоненты Пользовательского Интерфейса
- **Задача:** Разработка современного SPA на React, TypeScript.
- **Компоненты (`web_ui/src/components/`):**
  - [x] `SafetyDashboardView`: графики инцидентов и общий индекс безопасности.
  - [x] `KnowledgeGraphView`: 2D/3D визуализатор графа связей сущностей и концептов.
  - [x] `AgentSwarmView`: интерактивная топология роя агентов.
  - [x] `ConstitutionViewer`: просмотрщик 67 статей конституции со статусом соблюдения.
  - [x] `MLModelRegistryView`: реестр моделей ML с хэшами весов и стадиями `staging`/`production`.

#### WBS 3.2 — Интеграция Real-Time SSE/WebSocket
- **Задача:** Подключение клиента к WebSocket каналу сервера AIOS для обновления метрик без перезагрузки.
- **Модули:** `web_ui/src/services/aiosApi.ts`, `web_ui/src/App.tsx`
- **Критерии приемки:**
  - [x] Автоматический фаллбэк WebSocket ➔ REST Polling.

#### WBS 3.3 — Сборка и Встраивание в Сервер
- **Задача:** Добавление API эндпоинтов в Starlette (`aios_core/api/app.py`) для питания всех компонентов UI.
- **Тесты:** `tests/test_web_ui_integration.py` (все 540 тестов пройдены)

---

### ⚡ Milestone 4.2.4: Enterprise Scaling & PostgreSQL Support (Недели 11–12)

#### WBS 4.1 — Абстракция Хранилища с Поддержкой PostgreSQL
- **Задача:** Двухуровневый адаптер баз данных (SQLite для локального запуска, PostgreSQL / SQLAlchemy Async for production cluster).
- **Модули:** `aios_core/storage.py`

#### WBS 4.2 — Распределенный Rate Limiter & Circuit Breaker
- **Задача:** Защита от перегрузки на базе Redis/In-Memory скользящего окна.
- **Модули:** `aios_core/rate_limiter.py`, `aios_core/circuit_breaker.py`

#### WBS 4.3 — Расширение Helm Chart и HPA
- **Задача:** Добавление правил Kubernetes Horizontal Pod Autoscaler на основе метрик очереди задач и загрузки CPU.
- **Файлы:** `helm/aios/templates/hpa.yaml`, `helm/aios/values.yaml`

---

## 🎯 Сводная Матрица Приёмки (Acceptance Metrics)

| Метрика | Целевой Показатель v4.2 |
|---|---|
| **Общее количество тестов** | ≥ 580 passed tests |
| **Задержка ML-прогноза (ONNX)** | < 10 мс |
| **Время восстановления из бэкапа** | < 3 секунд |
| **Покрытие трассировкой OpenTelemetry** | 100% вызовов меж-агентных событий |
| **Время загрузки Web UI SPA** | < 1.2 секунды |
