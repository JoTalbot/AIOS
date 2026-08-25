# Жизненный цикл контурной задачи

Реализовано в `aios_core/openhands/runner.py` (`OHOrchestrator.run`) поверх
`state_machine.py`. Каждый переход проходит `transition()` — проверяет
допустимость, засчитывает гейт исходящей стадии и лимит retry.

## Маршрут MVP

```
PENDING → PLANNING → READY → RUNNING → TESTING → REVIEW → (SECURITY_REVIEW) → (QA) → COMPLETED
```

Стадии и разговоры ролей:

| Статус | Роль разговора | Переход |
|---|---|---|
| PLANNING | Architect | → READY |
| READY | Coder | → RUNNING |
| RUNNING | Tester | → TESTING |
| TESTING | Reviewer | → REVIEW (гейт `tests` засчитан) |
| REVIEW | Security (если гейт) | гейт `review`; далее по required_gates |
| SECURITY_REVIEW | QA (если гейт) | гейт `security_review` |
| QA | — | гейт `qa` → COMPLETED |

Маршрут после TESTING/REVIEW выбирается по `extras.required_gates`
(`_stage_of`): опциональные security/qa-стадии включаются только когда гейт
заявлен. `REVIEW → COMPLETED` легален при default-гейтах `tests+review` —
гейт review засчитывается на самом переходе.

## Ошибки и retry

- Ошибка стадии PLANNING/RUNNING/TESTING/QA → FAILED; REVIEW/SECURITY_REVIEW → BLOCKED.
- FAILED/BLOCKED → PLANNING — retry, счётчик в `extras.retry_count`, лимит `max_retries` (default 3).
- Лимит исчерпан → CANCELLED + `FailureReport` (reason, attempts, files_changed,
  suggested_next_step); решение фиксируется в аудите.
- `TransitionError` на gate-check (маршрут в COMPLETED без гейтов) — баг контура,
  пробрасывается, а не считается retry-able ошибкой стадии.
- `CHANGES_REQUESTED` от Reviewer → BLOCKED (вердикт парсится из событий разговора;
  при отсутствии маркера/недоступности events API — fallback APPROVED с аудитом
  `verdict_fallback`).

## Finalize (перед COMPLETED)

1. `GitHubHelper.changed_files(base_branch)` — diff ветки.
2. `check_paths` против protected/deny профиля оркестратора: запрещённые пути
   блокируют COMPLETED (задача не завершается с dirty-diff).
3. Push ветки + draft PR (если github-helper настроен; иначе стадия пропускается).
4. `pr_url` в `RunResult`.

## Персистентность

`ContourService` сохраняет задачу при submit и после run (`ContourStore`,
state dir по env). При старте сервис восстанавливает задачи; `status()` читает
store лениво — статус доступен после рестарта без повторного прогона.
