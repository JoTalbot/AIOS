---
name: scoped-agent-delegation
version: 1.0
description: Ограничивает sub-agent delegation по owner, issuer, task, role, identity, capability, expiry и revocation.
triggers: [delegation, sub-agent, ephemeral-credential, least-privilege]
dependencies: [python>=3.11]
llm_required: false
mcp_tools: []
---

# Scoped Agent Delegation

## Алгоритм
1. Issue grant с accountable `owner_id` и `delegated_by`.
2. Scope одновременно связывает task, role, agent identity и allowlisted capabilities.
3. Expiry обязана быть timezone-aware и проверяется непосредственно перед tool call.
4. Revocation и expiry fail closed; grant нельзя использовать в другом task/role/agent.
5. SpecialistInvocation хранит только grant ID; registry — authority source.
6. Supervisor adapter валидирует grant до создания governed Action.
7. Negative tests: expired, revoked, task mismatch, capability escalation, missing grant.

## Контроль и развитие
- [x] 45 architecture tests passed.
- [x] Expiry/scope enforcement до side effects.
- [ ] Cryptographic issuer signature and durable revocation registry.
