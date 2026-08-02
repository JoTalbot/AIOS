---
name: mesh-cleanup
description: Очистка mesh-топологии и оптимизация сетевой инфраструктуры для улучшения производительности.
---

# Mesh Cleanup

**Вектор**: quality
**Статус**: active
**Путь**: `/mnt/agents/-Octopus/skills/core/mesh-cleanup`

## Описание
Очистка mesh-топологии и оптимизация сетевой инфраструктуры для улучшения производительности.

## Цели
- Очистка неиспользуемых mesh узлов
- Оптимизация mesh топологии
- Детекция проблем с mesh
- Проверка mesh health

## Рутины

### `scan_mesh_nodes.py**
```python
# Скан mesh узлов
# Функция: scan_mesh_nodes()
```

### `cleanup_mesh.py**
```python
# Очистка mesh
# Функция: cleanup_mesh()
```

### `optimize_mesh_topology.py**
```python
# Оптимизация mesh топологии
# Функция: optimize_mesh_topology()
```

## Метрики
- `mesh_nodes_count`: Количество mesh узлов
- `mesh_nodes_active`: Активные mesh узлы
- `mesh_nodes_inactive`: Неактивные mesh узлы
- `mesh_cleanup_potential`: Потенциал очистки
- `mesh_health_score`: Оценка здоровья mesh

## Пример использования
```bash
# Скан mesh узлов
python3 code/scan_mesh_nodes.py

# Очистка mesh
python3 code/cleanup_mesh.py

# Оптимизация топологии
python3 code/optimize_mesh_topology.py
```

## Векторный coverage
- ✅ Mesh node scan
- ✅ Mesh cleanup
- ✅ Mesh topology optimization
- ✅ Mesh health monitoring

## Anti-patterns to fix
1. Too many mesh nodes
2. Inactive mesh nodes
3. Poor mesh topology
4. Mesh network issues
5. No mesh health checks

## Mesh best practices
- Keep active nodes only
- Regular topology cleanup
- Monitor mesh health
- Optimize mesh configuration
- Reduce mesh complexity

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
- Описание назначения: Очистка mesh-топологии и оптимизация сетевой инфраструктуры для улучшения производительности.
