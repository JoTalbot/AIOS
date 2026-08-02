---
name: swarm-load-forecaster
description: Predictive load analysis for the Octopus swarm. Collects real system metrics (CPU load, memory, disk, network), stores time-series history, computes moving averages, detects trends (rising/falling/stable), and forecasts 
---

# SKILL: swarm-load-forecaster
**Category:** core
**Status:** ACTIVE (systemd timer, 5-min intervals)
**Created:** 2026-06-20 (Batch 85, Phase 8)
**Path:** /opt/octopus-swarm-load-forecaster.py
**Data:** /var/lib/octopus/forecaster/metrics_history.json

## Description
Predictive load analysis for the Octopus swarm. Collects real system metrics (CPU load, memory, disk, network), stores time-series history, computes moving averages, detects trends (rising/falling/stable), and forecasts 1/2/4 hours ahead using linear regression. Generates alerts when thresholds are exceeded.

## Metrics Collected
- CPU Load (1/5/15 min)
- Memory (total/used/available/%)
- Disk (total/used/free/%)
- Network (RX/TX MB)

## Algorithms
- **Trend Analysis:** Compares recent vs older averages (5% change threshold)
- **Linear Forecast:** y = ax + b regression extrapolated to forecast horizon
- **Moving Average:** Rolling window of 5 data points

## Alert Thresholds
- Load 5min > 3.0 (warning)
- Memory > 85% (warning)
- Disk > 90% (critical)

## Commands
- Run once: `python3 /opt/octopus-swarm-load-forecaster.py`
- View history: `cat /var/lib/octopus/forecaster/metrics_history.json | jq`
- Timer status: `systemctl status octopus-forecaster.timer`
- Next trigger: `systemctl list-timers octopus-forecaster.timer`

## Integration
Feeds data to: Phase 8.3 (Resource Reclaimer), Phase 8.4 (Self-Modification)

## Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-отчёт: статус, найденные факты, риски, рекомендации, следующий bounded-шаг.
5. Если требуется изменение системы — записать proposal/rollback в logs/reports и ждать consent gate либо выполнения автономным агентом в bounded-режиме.
6. Для Telegram: прямые push-уведомления запрещены, кроме `skill-notification` и отчётов автономного агента.
7. Для AWS/платных ресурсов: только аудит; создание/включение ресурсов запрещено без явной команды человека.

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage и дописывает AI-предложения в `references/`.
- Развитие через ИИ: локальный Ollama/Qwen генерирует bounded improvement proposal; автоприменяются только безопасные структурные улучшения (алгоритм, тест, runtime wrapper).
- Описание назначения: Операционный навык Octopus: swarm-load-forecaster.
