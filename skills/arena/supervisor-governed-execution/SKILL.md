---
name: supervisor-governed-execution
version: 1.0
description: Связывает bounded supervisor graph с AIOS ArchitectureRuntime без прямого доступа sub-agents к capabilities.
triggers: [supervisor, delegation, specialist-execution, governed-tools]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# Supervisor Governed Execution

## Алгоритм

1. Для каждого selected role создать `SpecialistInvocation`: distinct agent identity,
   одна capability, bounded arguments, explicit authority.
2. Не передавать CapabilityEngine в supervisor executor.
3. `SupervisorRuntimeExecutor(role)` строит Action/ExecutionContext и вызывает только
   `ArchitectureRuntime.execute`.
4. Observation сохранять по role под lock: ExecutionEngine запускает независимые roles параллельно.
5. Governed deny преобразовать в executor failure, чтобы dependency graph остановил следующие batches.
6. Missing role invocation — fail closed до side effect.
7. Проверить: все selected roles имеют observation; policy event на каждый role; deny даёт 0 calls и 0 budget.

## Контроль и развитие
- [x] 43 architecture tests passed.
- [x] Supervisor не имеет direct capability reference.
- [x] Policy denial и missing invocation fail closed.
- [ ] Delegation expiry и owner metadata.
