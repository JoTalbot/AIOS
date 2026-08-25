---
name: architecture-approval-audit
version: 1.0
description: Добавляет one-shot human approval и tamper-evident correlation audit между AIOS policy decision и capability effect.
triggers: [human-approval, high-risk-action, append-only-audit, correlation-id]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# Architecture Approval Audit

## Алгоритм

1. Policy decision всегда выполняется и аудируется до approval.
2. Approval request привязывается к `action_id`, `task_id`, identity и capability.
3. Статусы только PENDING → APPROVED/REJECTED → CONSUMED; повторное решение и replay fail closed.
4. APPROVED consume происходит до runtime/PEP и допускает ровно один execution attempt.
5. Каждый architecture event получает correlation `task_id:action_id`.
6. Persistent JSONL record включает `previous_hash`; hash считается по canonical sorted JSON.
7. Verify пересчитывает всю цепь и обнаруживает изменение payload/order/link.
8. В тестах обязательно: pending, approve+execute, replay deny, reject deny, capability calls 0 для deny, tamper detection.

## Контроль и развитие

- [x] 40 architecture regression tests passed.
- [x] Approval не расходует budget до разрешения.
- [x] Hash chain и correlation протестированы.
- [ ] Authenticated transport и durable append-only backend.
