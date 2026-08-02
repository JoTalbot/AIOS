---
name: autopilot-runtime-durability-guard
description: Этот скил предназначен для...
---

# SKILL: autopilot-runtime-durability-guard

## Описание

Этот скил предназначен для...

**Category:** core / reliability / security
**Status:** ACTIVE

## Purpose
Prevents the public Octopus autopilot API from silently running as an unmanaged orphan with missing source or token material.

## Алгоритм
1. Verify source exists and root-only token has mode 0600.
2. Verify service is active and enabled.
3. Verify runtime PID belongs to `system.slice/octopus-autopilot-api.service`, not an abandoned user session.
4. Verify argv references the durable canonical source.
5. Verify loopback listener on 8787.
6. Run local and external health plus negative/positive auth canaries.
7. Emit only booleans; never emit token values.

## Runtime
`python3 code/run.py`

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py`.
