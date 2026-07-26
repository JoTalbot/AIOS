# Evolution Engine Integration

## Автоматический запуск
Эволюция запускается автоматически каждые 6 часов через ARQ worker.

Ручной запуск:
```bash
curl -X POST http://localhost:8080/api/v1/evolution/run \
  -H "Authorization: Bearer <admin_token>"
```

## Уведомления
Настройте в .env:
```
EVOLUTION_ALERT_EMAILS=admin@yourdomain.com
```

Система отправит email когда:
- Шаблон автоматически улучшен (A/B тест)
- Обнаружен новый интент
- Self-healing активирован

## Метрики (Prometheus)
- `aios_evolution_cycles_total` - количество циклов эволюции
- `aios_templates_promoted_total{template_id="..."}` - продвижения шаблонов
- `aios_new_intents_discovered_total{intent_name="..."}` - новые интенты
- `aios_self_heal_attempts_total{status="..."}` - попытки self-healing

## Dashboard
Откройте http://localhost:8080/advisor/evolution для просмотра:
- История циклов эволюции
- Статистика улучшений
- Кнопка ручного запуска
