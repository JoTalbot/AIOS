# AIOS на пробном аккаунте Fly.io

Этот профиль предназначен для короткой демонстрации AIOS без платной инфраструктуры.
Он запускает облегчённый FastAPI/P2P API и по запросу может обращаться к OpenRouter.
Полный стек с Android, PyTorch, Qiskit, ChromaDB, Redis, PostgreSQL, Grafana и
фоновыми воркерами в этот профиль намеренно не входит.

## Ограничения пробного аккаунта

По актуальной документации Fly.io пробный период включает:

- 2 часа суммарной работы виртуальных машин или 7 дней доступа — что наступит раньше;
- автоматическую остановку пробной машины после 5 минут работы;
- до 2 vCPU и 4 ГБ RAM на машину;
- отсутствие GPU и выделенного IPv4.

После исчерпания trial приложение остановится до добавления способа оплаты.
Источник: <https://fly.io/docs/about/free-trial/>.

## Что развёртывается

- приложение: `jotalbot-aios-trial-2026`;
- регион: `arn` (Стокгольм; `waw` больше не принимает новые ресурсы Fly.io);
- машина: `shared`, 1 vCPU, 512 МБ RAM;
- автозапуск при HTTP-запросе;
- остановка без трафика, `min_machines_running = 0`;
- отдельный `Dockerfile.fly` и минимальный `requirements-fly.txt`;
- без постоянного диска: состояние после замены машины не гарантируется.

Точки входа после деплоя:

- `https://jotalbot-aios-trial-2026.fly.dev/` — информация о сервисе;
- `https://jotalbot-aios-trial-2026.fly.dev/health` — health check;
- `https://jotalbot-aios-trial-2026.fly.dev/docs` — Swagger UI;
- `https://jotalbot-aios-trial-2026.fly.dev/api/p2p/discover` — discovery узла;
- `POST https://jotalbot-aios-trial-2026.fly.dev/api/swarm/debate` — запрос к LLM-рою.

## Безопасная настройка GitHub Actions

Не передавайте Fly.io-токен в коммитах, issue или сообщениях.

1. Если приложение ещё не создано, сформируйте временный org-scoped token —
   workflow сможет создать приложение автоматически:

   ```bash
   fly tokens create org --name "AIOS GitHub deploy" --expiry 24h
   ```

   После первого деплоя рекомендуется заменить его ограниченным токеном приложения:

   ```bash
   fly tokens create deploy -a jotalbot-aios-trial-2026
   ```

2. Откройте репозиторий GitHub:
   `Settings → Secrets and variables → Actions → New repository secret`.
3. Создайте секрет `FLY_API_TOKEN` и вставьте полученный токен.
4. Запустите workflow вручную:
   `Actions → Deploy Fly.io Trial → Run workflow`.

Автоматический деплой при push намеренно отключён, чтобы обычные изменения в
`main` не расходовали ограниченное время Fly.io Trial. Если секрет отсутствует,
workflow корректно пропускает деплой.

## OpenRouter

Для реальных ответов роя добавьте ключ как Fly secret:

```bash
fly secrets set OPENROUTER_API_KEY="..." -a jotalbot-aios-trial-2026
```

Если ключ отсутствует, `/api/swarm/debate` работает в безопасном mock-режиме.
Ключ никогда не должен находиться в `fly.toml`, `.env.example` или исходном коде.

Пример запроса:

```bash
curl -X POST "https://jotalbot-aios-trial-2026.fly.dev/api/swarm/debate" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Предложи план проверки нового API"}'
```

## Локальная проверка образа

```bash
docker build -f Dockerfile.fly -t aios-fly-trial .
docker run --rm -p 8000:8000 aios-fly-trial
curl http://localhost:8000/health
```

## Важное отличие от production

Trial-профиль — только демонстрационный API. Для постоянной работы понадобятся
платный Fly.io Pay As You Go, постоянный volume или внешняя база, отдельные
воркеры и контролируемое хранение секретов.
