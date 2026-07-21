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
# deploy/monitoring/grafana-aios-ops.json (paste JSON)
```

Без docker любой Prometheus-совместимый агент (vmagent, alloy, node-
exporter textfile) читает тот же `/metrics` напрямую curl'ом:

```bash
curl -s http://127.0.0.1:8000/metrics | grep '^aios_'
```

Наряду с endpoint есть read-only ops-панель без зависимостей:
`http://127.0.0.1:8000/dashboard` (очередь, устройства, профили, шарды).
