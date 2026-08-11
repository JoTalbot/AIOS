# AIOS Ops-наблюдаемость (локальный стек)

`GET /metrics` AIOS REST-агента с 9.0.0-alpha.21 отдаёт Prometheus text
exposition format с gauges флота:

| Метрика | Смысл |
| --- | --- |
| `aios_shard_jobs{status=...}` | записи очереди pull-джобов по статусам |
| `aios_shard_job_queue_depth` | глубина очереди (pending+claimed) |
| `aios_shard_jobs_stale_claimed` | зависшие claim'ы за TTL |
| `aios_shard_hosts` | живые shard-host воркеры |
| `aios_devices{state=...}` | пул устройств (registered/free/leased) |
| `aios_device_limits` | количество заданных квот пула |
| `aios_profiles_total`, `aios_profiles{platform=...}` | профили аккаунтов |
| `aios_catalog_platforms` | платформы в YAML-каталоге |
| `aios_seen_receipts{platform,kind}` | записанные показы/встречи (ad/video) из per-platform БД `data/*.sqlite` |
| `aios_outbox_pending{platform}` | черновики guarded outbox, ждущие одобрения |
| `aios_telegram_delivery_success_ratio` | rolling success ratio Telegram delivery |
| `aios_telegram_latency_seconds{phase,quantile}` | generation/send/total p50/p95 |
| `aios_telegram_queue_jobs{queue,status}` | durable generation/outbox rows |
| `aios_telegram_canary_ok`, `aios_telegram_canary_age_seconds` | полный silent sendMessage canary и его свежесть |

Telegram-бот поднимает redacted exporter на `:9103/metrics`; payload сообщений,
chat ID, token, tunnel URL и Bearer keys в метрики не попадают. Docker Compose
передаёт Prometheus доступ к host exporter через `host.docker.internal`.

## Alert-правила

`aios-alerts.yml` (уже подключён в `prometheus.yml` через `rule_files`):
падение агента / отсутствие живых shard-worker'ов при pending-джобах,
бэклог очереди (>50 warning, >200 critical), зависшие claim'ы,
исчерпание пула устройств, отставание одобрения outbox (>100 за час),
а также Telegram exporter/canary, ambiguous delivery, generation backlog и
Telegram delivery SLO. Группы видны в Prometheus → Alerts; роутинг в Alertmanager настраивается
на вашей стороне.

## Prometheus (docker)

```bash
docker run --rm --network host \
  -v "$PWD/deploy/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" \
  prom/prometheus:v2.53.0
```

Prometheus слушает `http://127.0.0.1:9090`, цель — AIOS на
`http://127.0.0.1:8000/metrics`.

## Grafana

```bash
docker run --rm --network host --name aios-grafana -d grafana/grafana
# http://127.0.0.1:3000 (admin/admin) → Add data source → Prometheus
# → URL http://127.0.0.1:9090 → Import dashboard →
# deploy/monitoring/grafana-aios-ops.json и
# deploy/monitoring/grafana-telegram-llm.json (paste JSON)
```

Без docker любой Prometheus-совместимый агент (vmagent, alloy, node-
exporter textfile) читает тот же `/metrics` напрямую curl'ом:

```bash
curl -s http://127.0.0.1:8000/metrics | grep '^aios_'
```

Наряду с endpoint есть read-only ops-панель без зависимостей:
`http://127.0.0.1:8000/dashboard` (очередь, устройства, профили, шарды).
