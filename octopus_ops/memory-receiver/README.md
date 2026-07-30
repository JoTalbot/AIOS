# Octopus Fly.io memory receiver (prep only)

Назначение: минимальная внешняя нода для HTTP-репликации ПАМЯТИ без SSH.

Что умеет:
- `GET /healthz`
- `POST /api/v1/memory/replicate` — HMAC/timestamp/nonce, сохранение файла по `sha256`
- `GET /api/v1/memory/blob?ref=sha256:...` — HMAC/timestamp/nonce, выдача сохранённого blob

Файлы:
- `app.py` — standalone receiver на stdlib Python
- `Dockerfile` — контейнер для Fly.io
- `fly.toml` — конфиг Fly deploy

Почему только prep:
- аккаунт Fly.io пустой;
- у Fly.io нет постоянного free tier, поэтому app/volume не создаются автоматически;
- для реального запуска нужна явная команда пользователя.

Пример ручных шагов после подтверждения пользователя:
1. `flyctl apps create <unique-app-name> --org personal`
2. `flyctl volumes create octopus_memory_data --size 1 --region fra -a <app>`
3. `flyctl secrets set OCTOPUS_REPLICATION_HMAC_SECRET=... -a <app>`
4. `flyctl deploy -a <app>`
5. добавить `memory_replicate_url` в `/var/lib/octopus/nodes.json`

Локальная проверка без Fly:
```bash
docker build -t octopus-fly-memory-receiver .
docker run --rm -p 127.0.0.1:18080:8080 \
  -e OCTOPUS_REPLICATION_HMAC_SECRET='replace-with-32+chars' \
  octopus-fly-memory-receiver
curl http://127.0.0.1:18080/healthz
```
