# AIOS v20 Architecture Direction

## Цель

Переход от набора автономных компонентов к управляемой самоэволюционирующей платформе агентов.

## Архитектурные слои

### 1. Control Plane

Единый слой управления:

- Agent Registry
- Policy Engine
- Task Planner
- Lifecycle Manager
- Audit Trail

Control Plane не выполняет бизнес-задачи напрямую, а принимает решения и маршрутизирует выполнение.

### 2. Agent Runtime Plane

Изолированное выполнение агентов:

- skills loading
- tool permissions
- context management
- memory access
- execution sandbox

Каждый агент должен иметь явный контракт входов, выходов и разрешений.

### 3. Knowledge Plane

Объединение:

- RAG
- project memory
- session handoff
- validated skills
- telemetry knowledge

Источник истины: проверенные артефакты, а не необработанные логи.

### 4. Evolution Plane

Безопасная эволюция системы:

- proposal generation
- impact analysis
- tests gate
- approval policy
- rollout tracking

Изменения должны проходить через проверяемый цикл, а не появляться магией из очередного LLM-запроса. Магия отлично выглядит в демо, но ломает продакшен с удивительным постоянством.

## Главные инварианты

1. Все агенты имеют идентичность и журнал действий.
2. Все изменения кода проходят через тестовый контур.
3. Protected components остаются под контролем владельца.
4. Memory хранит решения и причины, а не только текст.
5. Observability является частью архитектуры, а не последним костылём.

## Следующие инженерные этапы

1. Инвентаризация текущих модулей и связей.
2. Выделение стабильных API-контрактов между слоями.
3. Создание migration map v19 → v20.
4. Добавление архитектурных тестов границ модулей.
5. Постепенный rollout без остановки production.
