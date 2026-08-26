# AIOS v20 Architecture Iteration Plan

Цель: последовательная миграция AIOS к модульной self-evolving архитектуре без разрушения production-контуров.

## Iterations

1. Architecture baseline: карта текущих компонентов и контрактов.
2. Domain boundaries: разделение core, agents, knowledge, evolution.
3. Stable API contracts: единые интерфейсы модулей.
4. Agent runtime isolation: изоляция выполнения агентов.
5. Event bus layer: события между подсистемами.
6. Memory architecture: унификация short/long term memory.
7. Knowledge plane: RAG и источники знаний.
8. Skills registry: версионирование и жизненный цикл skills.
9. Evolution engine: безопасное самоулучшение.
10. Evaluation framework: автоматическая проверка изменений.
11. Security layer: политики доступа и audit.
12. Observability: метрики, трассировка, диагностика.
13. Deployment abstraction: единый runtime deployment.
14. Multi-machine coordination: синхронизация агентов.
15. API gateway cleanup: стабильный внешний API.
16. Plugin architecture: расширения без изменения ядра.
17. Data contracts: схемы и миграции данных.
18. Failure recovery: восстановление после сбоев.
19. Production hardening: нагрузочные и регрессионные тесты.
20. AIOS v20 release: фиксация архитектурного стандарта.

## Правила

- Не ломать production.
- Малые атомарные изменения.
- Каждый этап имеет тесты и журнал сессии.
- Protected-файлы изменяются только по специальной процедуре.
