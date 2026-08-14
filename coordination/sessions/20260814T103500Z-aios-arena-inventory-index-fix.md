# Сессия: inventory из Git index, не worktree

---
session_id: "20260814T103500Z-aios-arena-inventory-index-fix"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T10:35:00Z"
updated_utc: "2026-08-14T10:35:00Z"
branch: "agent/20260814-project-inventory"
base_commit: "2af3651a"
claim: "coordination/claims/inventory-index--20260814T103500Z-aios-arena-inventory-index-fix.md"
---

## Причина

После merge основной worktree с чужим unstaged LLM diff сделал inventory stale. Generator должен читать Git index blobs, а не mutable worktree.

## План

Перевести чтение на `git ls-files -s` + `git cat-file --batch`, добавить regression для unstaged README mutation и повторить check в грязном `/root/AIOS`.
