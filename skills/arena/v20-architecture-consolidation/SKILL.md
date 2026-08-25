---
name: v20-architecture-consolidation
version: 1.0
description: Консолидирует AIOS v20 policy kernel, runtime enforcement, execution PEP и supervisor без обхода side-effect boundary.
triggers: [aios-v20, architecture, execution-kernel, supervisor, policy-enforcement]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# V20 Architecture Consolidation

## Описание

Использовать при переносе архитектурных веток в канонический стек. Policy и execution
kernel — не конкурирующие реализации: первый является PDP/control plane, второй —
PEP/data plane. Их связывает только composition root.

## Алгоритм

1. Инвентаризировать source PR по файлам/контрактам; не переносить workflow,
   coordination dashboard или generated inventory из feature branches.
2. Импортировать один seam с его regression tests.
3. Нормализовать CapabilityEngine envelope в `Observation`: transport keys `success/error`
   не должны протекать в domain `result`.
4. Composition order: identity/trust/policy/audit → RUNNING → heartbeat → budget → execute.
5. Deny/error до PEP проверять assertions: capability calls = 0, budget не расходуется.
6. Supervisor остаётся deterministic и bounded; план/graph не дают права на side effect.
7. Legacy/protected orchestrator подключать только adapter boundary, не wholesale rewrite.
8. Проверки: весь kernel/runtime/execution/supervisor/architecture набор, ruff, py_compile,
   size budget, generated inventory.

## Контроль и развитие

- [x] PDP и PEP связаны единым `ArchitectureRuntime`.
- [x] Supervisor plan доступен через тот же composition root.
- [x] Allow/deny/lifecycle/budget/unknown identity regression tests.
- [ ] Persistent audit + human approval gate.
- [ ] OpenHands backend adapter после снятия чужого claim.
