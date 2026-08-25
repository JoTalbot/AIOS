---
name: v20-kernel-contract
version: 1.0
description: Проверка и реализация fail-closed цепочки AIOS v20 identity → trust → policy → audit и bounded runtime primitives.
triggers: [v20-kernel, policy-decision, trust-manager, agent-runtime]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# V20 Kernel Contract

## Описание

Применять при развитии `aios_core/kernel` и `aios_core/runtime`. Главный инвариант:
неизвестные identity/capability/trust и исчерпанные runtime budgets не должны молча
разрешать действие; каждое полученное policy decision должно быть структурированно
зафиксировано без мутации объекта решения.

## Алгоритм

1. Сверить сигнатуры всей цепочки, а не только отдельных классов: `ExecutionContext.action`
   должен стать capability policy engine, а не передаваться как несовместимый объект.
2. Identity: валидировать через registry; неизвестный ID отклонять до policy evaluation.
3. Trust: разрешать только перечисленные уровни; default — `T0`.
4. Policy: явный grant + capability identity + достаточный trust; любое неизвестное значение
   даёт deny с машиночитаемой причиной.
5. Audit: принимать dataclass/dict, копировать payload, писать timezone-aware UTC timestamp,
   возвращать defensive copies.
6. Runtime: lifecycle только по допустимым переходам; heartbeat через monotonic TTL;
   budget запрещает consume после лимита.
7. Проверки: targeted kernel tests, ruff, py_compile, module-size budget.

## Контроль и развитие

- [x] Полная цепочка покрыта allow/deny/unknown identity tests.
- [x] Audit не мутирует вход и не раскрывает внутреннее состояние.
- [x] Heartbeat TTL, lifecycle transitions и action budget протестированы.
- [ ] Добавить persistent/append-only audit sink перед production wiring.
- [ ] Связать policy decision point с отдельным execution enforcement point.
