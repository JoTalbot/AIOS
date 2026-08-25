---
name: github-ci-baseline
version: 1.0
description: Диагностирует GitHub Actions через Checks API, отделяет main baseline от PR-specific failures и безопасно исправляет SHA-pinned actions.
triggers: [github-actions, red-ci, check-run, codeql, trivy]
dependencies: [gh]
llm_required: false
mcp_tools: []
---

# GitHub CI Baseline

## Описание

Использовать при массово красных checks, особенно когда загрузка workflow logs через
`gh run view --log-failed` завершается EOF. Не считать каждый failure дефектом PR:
сначала сравнить с последним run на `main` того же commit generation.

## Алгоритм

1. `gh run list --branch main --json ...` — получить baseline conclusions.
2. `gh pr checks <PR>` — классифицировать failed/success/skipped checks.
3. Для точной причины без logs использовать:
   `gh api repos/OWNER/REPO/check-runs/JOB_ID` и `/annotations`.
4. Проверить failed steps через `gh run view RUN --json jobs`; skipped/neutral не
   приравнивать к failure.
5. Для action version mismatch все steps одного action pin на один SHA; upstream tag
   object и commit проверять через `repos/OWNER/REPO/git/ref/tags/vN` и `git/tags/SHA`.
6. Проверить YAML parse и `python scripts/verify_supply_chain_pins.py`.
7. Trivy failure не обходить новым ignore без CVE/package/fixed-version; при недоступном
   registry оставить точный blocker и не менять digest вслепую.

## Контроль и развитие

- [x] Работает при недоступных zipped logs через Checks annotations.
- [x] CodeQL mixed-version диагностирован по annotation.
- [x] Supply-chain SHA validation включена.
- [ ] Добавить автоматический baseline comparator для всех открытых PR.
