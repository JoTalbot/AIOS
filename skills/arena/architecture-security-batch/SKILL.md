---
name: architecture-security-batch
version: 1.0
description: Параллельный bounded batch для signing, replay, delegation, idempotency, capability risk, audit query и health controls.
triggers: [security-batch, hmac, replay, idempotency, architecture-health]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# Architecture Security Batch

## Алгоритм
1. Разделить независимые primitives и создавать их параллельно.
2. Canonical JSON + injected 32-byte key + HMAC compare_digest.
3. Auth command подписывает action/decision/actor/timestamp/nonce/key-id; nonce consume only after valid signature/freshness.
4. Delegation signature покрывает grant ID и весь scope; child chain только сужает scope/lifetime.
5. Idempotency key всегда связан с immutable fingerprint.
6. Capability registry хранит owner/risk/enabled; risk profile детерминированно включает approval/audit/TTL.
7. Audit query остаётся read-only; health проверяет chain и pending approvals.
8. Завершить единым regression gate всех architecture layers.

## Контроль и развитие
- [x] 10 iterations integrated.
- [x] 48 architecture tests passed.
- [x] Ruff/compile/size budget clean.
- [ ] Asymmetric signatures, persistent nonce/idempotency stores, WORM audit backend.
