---
name: incident-triage
version: 1.0
description: Классификация и приоритизация системных инцидентов
triggers: [incident_check, health_alert, monitoring]
dependencies: []
llm_required: false
mcp_tools: []
---
# Incident Triage Skill

## Описание
Классифицирует системные инциденты по severity и типам.

## Severity Levels
| Level | Name | Description |
| SEV1 | CRITICAL | Полный outage |
| SEV2 | HIGH | Основной функционал недоступен |
| SEV3 | MEDIUM | Частичный outage |
| SEV4 | LOW | Косметические проблемы |

## Incident Types
- disk_full, high_error_rate, slow_response, memory_leak, network_issue
