# AIOS v20 — каноническая архитектура

Статус: foundation в draft PR #248. Этот документ фиксирует единственную целевую
структуру вместо параллельного развития PR #244–#247.

## Поток выполнения

```text
SupervisorTask
    ↓ AgentSupervisor / ExecutionGraphBuilder
Specialist plan (bounded, deterministic)
    ↓
Action + ExecutionContext
    ↓
ArchitectureRuntime                 ← composition root
    ├─ Policy Kernel (PDP/control plane)
    │    IdentityRegistry → TrustManager → PolicyEngine → AuditLogger
    ├─ Runtime enforcement
    │    Lifecycle RUNNING → heartbeat alive → AgentBudget
    └─ Execution Kernel (PEP/data plane)
         CapabilityEngine.execute → Observation
```

Главный инвариант: capability side effect недостижим, пока policy decision не разрешил
действие и runtime enforcement не подтвердил lifecycle, heartbeat и budget.

## Владение ответственностью

| Компонент | Путь | Ответственность |
|---|---|---|
| Policy decision point | `aios_core/kernel/` | identity, trust, allow/deny reason, audit decision |
| Runtime enforcement | `aios_core/runtime/` | lifecycle, liveness, per-agent action budget |
| Policy enforcement point | `aios_core/execution/` | единственная граница capability side effects, normalized Observation |
| Agent supervisor | `aios_core/supervisor/` | bounded team selection, dependency graph, aggregation; не исполняет capability напрямую |
| Composition root | `aios_core/architecture/` | строгий порядок PDP → runtime checks → PEP и общий public boundary |
| Legacy integration | `aios_core/execution/orchestrator_*.py` | адаптеры без изменения protected `aios_core/orchestrator.py` |

## Fail-closed правила

- неизвестная identity → `policy_error`, capability не вызывается;
- отсутствующий policy grant / capability / trust → audited deny;
- agent не RUNNING, heartbeat stale или budget отсутствует/исчерпан → execution deny;
- structured CapabilityEngine envelope нормализуется: `result` не содержит transport envelope;
- Supervisor ограничен `budget_agents`, а graph валидируется до запуска executor;
- OpenHands и legacy Orchestrator должны входить через adapters, а не обходить
  `ArchitectureRuntime.execute()`.

## Консолидация веток

- PR #247 (`feature/aios-v20-kernel-bootstrap`) → усиленный `aios_core/kernel` и runtime в #248;
- PR #245 (`feat/execution-kernel-v1`) → `aios_core/execution` в #248;
- PR #246 (`feat/execution-kernel-wiring`) → regression boundary сохранён адаптерами;
  protected Orchestrator пока не патчится;
- PR #244 (`aios-supervisor-v1`) → `aios_core/supervisor` в #248;
- PR #243 (OpenHands) остаётся отдельным agent backend и должен подключаться через
  supervisor/execution adapters после снятия его coordination claim.

## Следующие этапы

1. Persistent append-only audit sink и correlation `task_id/action_id`.
2. Adapter `Supervisor ExecutionEngine → ArchitectureRuntime.execute` для role capabilities.
3. Human approval gate между PDP и PEP для high-risk действий.
4. Точечный patch protected Orchestrator только после отдельного review/selfguard workflow.
5. Удаление/закрытие superseded draft PR после подтверждения владельца — без автоматического merge.
