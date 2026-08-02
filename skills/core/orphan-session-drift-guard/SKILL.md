---
name: orphan-session-drift-guard
description: Этот скил предназначен для...
---

# SKILL: orphan-session-drift-guard

## Описание

Этот скил предназначен для...

**Category:** core / reliability / resource hygiene
**Status:** ACTIVE

## Purpose
Read-only detection of abandoned systemd sessions containing strongly classified stale or runaway PPid=1 processes. It never kills or signals a process.

## Алгоритм
1. Enumerate only `session-*.scope` units and read cgroup membership.
2. Classify only scopes with `SubState=abandoned`.
3. Candidate requires PPid=1, age >=1h, and either known stale scanner (`grep`/`head`) or CPU >=90%.
4. Never include command arguments, environment or secrets in output.
5. Emit proposal only (`actions_taken=0`); termination requires separate bounded review.

## Research basis
systemd documents that `KillUserProcesses=no` leaves scopes abandoned. Intentionally persistent work should be moved into a real system/user service rather than left inside login sessions.

## Runtime
`python3 code/run.py`

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
