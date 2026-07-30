---
name: disk-growth-forecast
version: 1.0
description: Прогнозирование роста диска на основе истории
triggers: [disk_check, disk_forecast, capacity_planning]
dependencies: []
llm_required: false
mcp_tools: []
---
# Disk Growth Forecast Skill

## Описание
Предсказывает когда диск заполнится на основе линейной регрессии по истории использования.

## Формула
```
days_until_full = (100 - current_percent) / daily_growth_rate
estimated_full_date = today + days_until_full
```

## Thresholds
- >30 days: OK
- 14-30 days: WARNING
- 7-14 days: ALERT
- <7 days: CRITICAL
