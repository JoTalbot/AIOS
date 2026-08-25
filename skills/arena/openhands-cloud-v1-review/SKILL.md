---
name: openhands-cloud-v1-review
version: 1.0
description: Проверяет OpenHands Cloud V1 start-task/conversation lifecycle и воспроизводит CI head без изменения чужой branch.
triggers: [openhands-cloud, specialist-spawner, app-conversation, pr-review]
dependencies: [git, gh, pytest]
llm_required: false
mcp_tools: []
---

# OpenHands Cloud V1 Review

## Описание

Использовать при review OpenHands-интеграции, когда branch занята другим агентом или
GitHub logs недоступны через signed URL. Проверка выполняется в `git archive` внутри
`/tmp`, не переключая session branch и не меняя claimed files.

## Алгоритм

1. Fetch remote branch в `refs/remotes/origin/...`; не checkout/switch.
2. `git archive <ref> | tar -x -C /tmp/review` и запустить точную CI-команду там.
3. Сверить enums между canonical `TaskStatus` и контурным `OHStatus`; импорт всего
   package может падать до тестов из-за неверного enum member.
4. Для Cloud V1 различать два ID:
   - POST возвращает start-task `id`;
   - terminal start-task возвращает `app_conversation_id`.
5. Не использовать start-task ID в `wait_execution`. Сначала `wait_start_task(id)`,
   затем извлечь conversation ID и только его опрашивать до terminal execution status.
6. Contract-test обязан моделировать реальный ответ `{id: st-1}` →
   `{status: READY, app_conversation_id: conv-1}`.
7. При ACTIVE чужом claim оставить точный PR review/handoff вместо прямой правки.

## Контроль и развитие

- [x] Воспроизведение через archive не загрязняет рабочую ветку.
- [x] Найдены `TaskStatus.QA` collection failure и V1 ID mapping defect.
- [x] Review опубликован в PR #243.
- [ ] После owner fix повторить dedicated audit workflow и Cloud contract tests.
