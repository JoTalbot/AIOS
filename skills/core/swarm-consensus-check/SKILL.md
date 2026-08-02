---
name: swarm-consensus-check
description: Проверка согласованности (consensus) в swarm кластере для выявления рассинхронизации узлов.
---

# Swarm Consensus Check

**Вектор**: swarm
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/swarm-consensus-check`

## Описание
Проверка согласованности (consensus) в swarm кластере для выявления рассинхронизации узлов.

## Цели
- Проверка согласованности кластера
- Детекция рассинхронизации узлов
- Мониторинг состояния swarm
- Обнаружение проблем с BFT-согласием

## Рутины

### `check_consensus.py`
```python
# Основная функция для проверки консенсуса
# Использует docker swarm для сбора метрик
```

### `detect_lag.py`
```python
# Детекция рассинхронизации между узлами
# Функция: detect_node_lag(timeout=60)
```

### `verify_bft.py`
```python
# Проверка BFT-согласия
# Функция: verify_bft_compliance()
```

## Метрики
- `nodes_synced`: Количество синхронизированных узлов
- `lag_nodes`: Количество отстающих узлов
- `consensus_percentage`: Процент согласия
- `bft_compliance`: Соответствие BFT протоколу
- `last_sync_time`: Последнее время синхронизации

## Пример использования
```bash
# Базовая проверка
python3 code/check_consensus.py

# Детекция рассинхронизации
python3 code/detect_lag.py

# Проверка BFT
python3 code/verify_bft.py
```

## Векторный coverage
- ✅ Swarm node sync
- ✅ BFT consensus verification
- ✅ Cluster state monitoring
- ✅ Latency detection

## Anti-patterns to fix
1. Node desynchronization
2. BFT consensus failures
3. Stale node states
4. Network partition issues
5. Leader election delays

## Known issues
- Node lag > 5%: warning
- BFT compliance < 90%: critical

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
- Описание назначения: Проверка согласованности (consensus) в swarm кластере для выявления рассинхронизации узлов.
