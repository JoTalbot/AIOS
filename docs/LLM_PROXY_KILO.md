# AIOS LLM Proxy и Kilo Code

## Назначение

`aios-llm-proxy.service` предоставляет локальный OpenAI-compatible API на `127.0.0.1:8099`:

- `GET /v1/models` — каталог доступных LLMBalancer models;
- `POST /v1/chat/completions` — chat, streaming SSE и native tool calls;
- `GET /` — краткий health/status.

Proxy не публикуется наружу и не должен указывать Colab endpoint на самого себя.

## Маршрутизация моделей

- `aios/auto`, `auto`, `llm-balancer`, `qwen2.5-coder` — smart fallback.
- Для tool calls auto предпочитает tool-capable provider/model.
- Явный model ID из `/v1/models` сохраняется при routing, где provider его поддерживает.
- Colab используется только при непустом config, отсутствии self-loop и resolvable tunnel host.
- При передаче auto alias в Colab upstream model нормализуется в `qwen2.5-coder`.

Пустой `content` вместе с `tool_calls` является успешным ответом. Legacy `function_call` нормализуется в SSE `tool_calls`.

## Kilo config

Config по умолчанию:

```text
~/.config/kilo/kilo.jsonc
```

Read-only проверка:

```bash
cd /root/AIOS
source /opt/aios/.venv/bin/activate
python scripts/sync_kilo_llm_models.py --check
```

Атомарная синхронизация:

```bash
python scripts/sync_kilo_llm_models.py
```

Sync изменяет только provider `aios`, сохраняет другие providers/options, mode файла и использует временный файл + `os.replace`. Default legacy `aios/qwen2.5-coder` переводится в `aios/auto`.

Для тестового config:

```bash
python scripts/sync_kilo_llm_models.py --config /tmp/kilo.jsonc
```

## Проверка и rollout

```bash
pytest -q tests/test_llm_proxy_models.py
curl -fsS http://127.0.0.1:8099/
curl -fsS http://127.0.0.1:8099/v1/models
systemctl restart aios-llm-proxy.service
systemctl --no-pager --full status aios-llm-proxy.service
```

Перед restart сохранить service status и последние логи. При ошибке откатить Git commit и перезапустить service. Не выводить API keys, `.llm_keys.json` или Kilo `apiKey` в чат/логи.
