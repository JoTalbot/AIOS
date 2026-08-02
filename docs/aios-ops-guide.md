# AIOS — Руководство по эксплуатации (Ops Guide)

> Сервер: 167.233.95.7 (root) | Ubuntu 22.04.5 | AIOS v16.0.0

## 1. Системные сервисы (systemd)

| Сервис | Статус | Описание | Команда |
|---|---|---|---|
| aios-auto-coder | active | Автокодер (LLM-агент) | systemctl restart aios-auto-coder |
| aios-auto-promote.timer | active | Авто-промоут (каждые 5 мин) | systemctl restart aios-auto-promote.timer |
| aios-telegram-bot | active | Telegram-бот | systemctl restart aios-telegram-bot |
| aios-exporter | active | Метрики (localhost:9101) | systemctl restart aios-exporter |
| ollama | active | Локальная LLM | systemctl restart ollama |
| nginx | active | Веб-сервер | systemctl restart nginx |
| ufw | active | Firewall | ufw status |

## 2. Docker-контейнеры

| Контейнер | Порты | Описание |
|---|---|---|
| aios-api | 127.0.0.1:8000 | FastAPI REST + метрики |
| aios-dashboard | 127.0.0.1:8080 | NiceGUI дашборд |
| aios-mcp | 127.0.0.1:8471 | MCP-шлюз |
| aios-prometheus | 127.0.0.1:9090 | Метрики |
| aios-grafana | 127.0.0.1:3000 | Визуализация |
| aios-autopilot | 8000 | Автопилот Instagram |

Управление: cd /root/AIOS && docker compose -f docker-compose.prod.yml up -d <имя>

## 3. Автокодер

5-фазный цикл каждые 180с: ANALYZE → PLAN → CODE → VALIDATE → COMMIT → авто-промоут → push

Логи:
- Циклы: tail -f /root/AIOS/logs/coder_orchestrator.log
- Промоуты: tail -f /root/AIOS/logs/auto_promote.log
- Бэкапы: tail -f /root/AIOS/logs/backup.log

Пути:
- Код: /root/AIOS-autocoder/run_coder_orchestrator.py
- Backlog: /root/AIOS-autocoder/data/coder_backlog.json
- Env: /etc/aios/aios-auto-coder.env
- Ветка: auto/coder-staging

Модели:
- Основная: gpt-4o-mini (внешняя через api.airforce)
- Fallback: локальная qwen2.5-coder:1.5b (Ollama)

## 4. Авто-промоут

- Скрипт: /usr/local/bin/aios-auto-promote.sh
- Timer: каждые 5 минут
- Логи: /root/AIOS/logs/auto_promote.log
- Действие: merge staging → main → push в GitHub

Защиты: junk-check, compile-валидация, conflict-abort, skip при незакоммиченных изменениях.

## 5. LLM-провайдеры

| Провайдер | Статус | Примечание |
|---|---|---|
| api.airforce | работает | gpt-4o-mini, 255 моделей |
| openrouter | нет баланса | 402 |
| huggingface | работает | резервный |
| aimlapi | нет баланса | 403 |
| ibm watsonx | нужен project_id | IAM-ключ есть |
| local (ollama) | работает | fallback |

## 6. Мониторинг

| Сервис | URL | Логин |
|---|---|---|
| Grafana | http://127.0.0.1:3000 | admin / GRAFANA_PASSWORD из .env |
| Prometheus | http://127.0.0.1:9090 | - |
| API /metrics | http://127.0.0.1:8000/metrics | - |

Дашборды: AIOS Production Exploitation, AIOS Autocoder

## 7. Бэкапы

- Когда: ежедневно 3:00 (cron) + 3:30 (timer)
- Скрипт: /root/AIOS/scripts/backup.sh
- Куда: /root/AIOS/backups/daily/
- Что: все БД + data + chroma + .env и конфиги
- Ротация: 14 дней

Ручной: bash /root/AIOS/scripts/backup.sh

## 8. Безопасность

- UFW: разрешены 22,80,443; закрыт 9101
- Cloudflare Access: защищает api.autosklo.org.ua
- Cloudflare WAF: rate-limit
- gitleaks: gitleaks detect --source /root/AIOS

## 9. Бизнес-функционал

- OLX-сборщик: active (~1921 объявление)
- Telegram-бот: active (@AIOScontrol_bot)
- API + вебхуки: работают, за Cloudflare Access
- Автопилот Instagram: active

## 10. Быстрые проверки

systemctl is-active aios-auto-coder aios-auto-promote.timer ollama nginx aios-telegram-bot aios-exporter
docker ps --filter name=aios
cd /root/AIOS && git rev-list --left-right --count main...origin/main  # 0 0
ls /root/AIOS-autocoder/tools/aios_*.py | wc -l  # 0
tail -5 /root/AIOS/logs/auto_promote.log

---

## 13. Защита от поломок (важно!)

Автокодер может создавать баги (однажды сломал MCPGateway → API упал). Для защиты:
- **API health-гейт** в авто-промоуте: перед промоутом код реально запускается (`create_app` + GET `/health`), при ошибке — `BLOCKED`.
- Цепочка промоута: `junk check → compile → API health → test gate → merge → push`.
- Если автокодер сломает импорт API — промоут не произойдёт, main останется чистым.

## 14. Авто-промоут (текущий)
- Timer: каждые **1 минуту** (`OnCalendar=*:0/1`).
- Скрипт: `/usr/local/bin/aios-auto-promote.sh`, версия в `deploy/aios-auto-promote.sh`.
- **Устойчив к параллельному агенту**: подтягивает origin, мержит чужие коммиты, rebase-retry при push.
- Логи: `/root/AIOS/logs/auto_promote.log`.

## 15. Обслуживание
- Docker build cache может расти (было 11GB) — очистить: `docker builder prune -f`.
- Мониторинг диска: `df -h /` (сейчас 40%, 44G свободно).
- `.bak*` файлы игнорируются git и должны удаляться.
- Очистка старых бэкапов автоматическая (14 дней).

## 16. Мониторинг автокодера
- Метрики автокодера: в exporter-файле `/app/data/metrics_exporter/aios_service.prom` (контейнер видит).
- Дашборд Grafana: "AIOS Autocoder" (uid=aios-autocoder), метрики `aios_cycle_*` через API.
- Логи циклов: `tail -f /root/AIOS/logs/coder_orchestrator.log`.
