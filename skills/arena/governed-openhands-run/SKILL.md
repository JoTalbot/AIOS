---
name: governed-openhands-run
version: 1.0
description: Запускает OpenHands Contour как governed capability только после policy, approval, runtime budget и audit gates.
triggers: [openhands-run, cloud-agent, governed-contour]
dependencies: [aios_core.architecture, aios_core.openhands]
llm_required: false
mcp_tools: []
---

# Governed OpenHands Run

## Алгоритм
1. Не вызывать `ContourService.run_task` из operator/API кода напрямую.
2. Обернуть contour в `OpenHandsCapabilityAdapter` и передать его ExecutionKernel.
3. Зарегистрировать distinct OpenHands agent identity с capability `openhands_cloud_run`.
4. Policy grant и trust должны быть explicit; capability обязана требовать ApprovalGate.
5. Первый run создаёт pending approval и не вызывает Cloud.
6. После authenticated approval повторить тот же deterministic action ID; только тогда PEP вызывает contour.
7. Audit correlation и budget должны подтверждать ровно один Cloud call.
8. Без `OPENHANDS_CLOUD_API_KEY` выполнять только FakeContour tests; реальные расходы требуют consent.

## Контроль и развитие
- [x] Policy deny и approval pending дают 0 contour calls.
- [x] Approved run даёт ровно 1 contour call, audit chain valid.
- [ ] Перевести HTTP router на governed runner после снятия чужого OpenHands claim.
