# Бесплатные LLM ключи для AIOS - Обновлено 2026-08-02

## Текущий статус (проверено логами)
- **OpenRouter 4 ключа**: ❌ ВСЕ мертвы HTTP 402 Payment Required
- **Groq 2 ключа**: ⚠️ Частично работают, но часто 429 Rate Limited
- **Airforce 3 ключа**: ❌ 429 часто
- **OpenAI 3 ключа**: ❌ 429
- **HuggingFace 3 ключа**: ❌ 402 / 504
- **Gemini 3 ключа**: ⚠️ Формат AQ... не стандартный AIza, возможно не работают
- **Mistral 3 ключа**: ⚠️ Работают только для mistral-small-latest, не для llama
- **Cohere 3 ключа**: ✅ Должны работать
- **DeepSeek 3 ключа**: ❌ 402
- **Z.ai 3 ключа**: ❌ token expired
- **Together, Cerebras, GitHub, Nvidia**: ❌ Не настроены, но бесплатны!

## Топ бесплатных провайдеров (без карты, 2026)

### 1. Groq (https://console.groq.com/keys) - САМЫЙ БЫСТРЫЙ, приоритет #1
- Бесплатно: 14k токенов/сек, без карты
- Модели: llama-3.3-70b-versatile (наш основной), llama-3.1-8b-instant (резерв)
- Лимит: 30 RPM, 14k TPM
- Сколько нужно: 5-10 ключей для ротации (каждый ключ отдельный аккаунт или тот же аккаунт дает 2 ключа)
- Как добавить:
  ```bash
  python3 scripts/add_free_llm_key.py --provider groq --key gsk_xxx
  ```

### 2. Cerebras (https://cloud.cerebras.ai) - БЕСПЛАТНО, 2k токенов/сек, без карты
- Модели: llama-3.3-70b, llama-3.1-8b
- Лимит: очень щедрый free tier
- Добавление:
  ```bash
  python3 scripts/add_free_llm_key.py --provider cerebras --key csk-xxx
  ```

### 3. GitHub Models (https://github.com/marketplace/models) - уже есть GITHUB_API_KEY, но не используется
- Бесплатно для любого GitHub аккаунта
- Модели: gpt-4o-mini, gpt-4o, Meta-Llama-3-70B, Mistral-small
- Endpoint: https://models.inference.ai.azure.com/chat/completions
- Ключ: GitHub PAT (у нас уже есть ghp_xxx)
- Мы добавили поддержку в balancer v2.2, нужен тест:
  ```bash
  python3 scripts/add_free_llm_key.py --test github
  ```

### 4. Together AI (https://api.together.ai/settings/api-keys)
- Бесплатно $25 кредитов при регистрации
- Модели: Meta-Llama-3-70B-Instruct-Turbo, Qwen2.5-72B
- ```bash
  python3 scripts/add_free_llm_key.py --provider together --key xxx
  ```

### 5. Mistral AI (https://console.mistral.ai/api-keys) - без карты
- Бесплатно: $5 кредитов, 1B токенов
- Модели: mistral-small-latest (работает!), open-mistral-7b
- У нас 3 ключа, но они используются для llama моделей (не работают). Нужно использовать mistral-small-latest
- Мы исправили: теперь mistral-small-latest в приоритете

### 6. Cohere (https://dashboard.cohere.com/api-keys) - без карты
- Бесплатно: 1000 calls/месяц
- Модели: command-r-08-2024, command-r7b
- У нас 3 ключа, должны работать

### 7. Google Gemini (https://aistudio.google.com/apikey) - без карты
- Бесплатно: 60 RPM
- Модели: gemini-2.0-flash, gemini-2.5-flash
- У нас 3 ключа формата AQ... - это не стандартный AIzaSy... ключ, возможно от Vertex? Нужно получить новые AIza...
- ```bash
  python3 scripts/add_free_llm_key.py --provider gemini --key AIzaSy...
  ```

### 8. OpenRouter Free Models (https://openrouter.ai/settings/keys)
- Бесплатно даже без баланса: openai/gpt-oss-20b:free, google/gemma-3-27b-it:free, mistralai/mistral-small-3.2-24b:free:factory
- Наши 4 ключа мертвы - нужно создать новый аккаунт и новый ключ
- ```bash
  python3 scripts/add_free_llm_key.py --provider openrouter --key sk-or-v1-...
  ```

### 9. NVIDIA NIM (https://build.nvidia.com) - без карты
- Бесплатно: 100+ моделей
- Модели: meta/llama-3.1-8b-instruct
- ```bash
  python3 scripts/add_free_llm_key.py --provider nvidia --key nvapi-...
  ```

## Быстрый скрипт добавления

Мы создали helper: `scripts/add_free_llm_key.py`

```bash
# Показать текущие ключи
python3 scripts/add_free_llm_key.py --list

# Добавить новый Groq ключ
python3 scripts/add_free_llm_key.py --provider groq --key gsk_...

# Протестировать провайдера
python3 scripts/add_free_llm_key.py --test groq
python3 scripts/add_free_llm_key.py --test cerebras
python3 scripts/add_free_llm_key.py --test github

# После добавления - перезапустить сервисы
systemctl restart aios-auto-coder
docker restart aios-api aios-mcp
```

## Рекомендуемый набор (минимум для стабильности)

- **5x Groq** (разные аккаунты) - основной провайдер, самый быстрый
- **3x Cerebras** - резерв #1, бесплатный, быстрый
- **2x Together** - резерв #2
- **2x GitHub Models** - используем существующий PAT + создать еще 1
- **2x Gemini** - новые AIza ключи
- **3x Mistral** - уже есть, но использовать для mistral-small-latest
- **2x OpenRouter free** - новые ключи с free моделями

Итого: ~15-20 ключей across 7 провайдеров = стабильность 99%.

## Как получить ключи за 10 минут

1. **Groq**: 
   - Иди на https://console.groq.com/keys
   - Login with Google
   - Create API Key -> скопируй gsk_...
   - Повтори для 2-3 аккаунтов (можно использовать +alias gmail)

2. **Cerebras**:
   - https://cloud.cerebras.ai -> Sign Up
   - API Keys -> Create
   - Скопируй csk-...

3. **GitHub Models**:
   - У тебя уже есть GITHUB_API_KEY=ghp_..., он работает для models endpoint
   - Мы добавили github провайдер в balancer, теперь он будет использоваться

4. **Together**:
   - https://api.together.ai -> Sign Up
   - Settings -> API Keys -> Create

5. **Gemini**:
   - https://aistudio.google.com/apikey -> Create API Key
   - Скопируй AIzaSy...

После добавления каждого ключа:
```bash
python3 scripts/add_free_llm_key.py --test <provider>
```

## Проверка балансировщика

```bash
cd /root/AIOS
/opt/aios/.venv/bin/python3.11 -c "from aios_core.llm_balancer import LLMBalancer; b=LLMBalancer(); print(b.status())"
/opt/aios/.venv/bin/python3.11 -m aios_core.llm_balancer --test  # если есть cli

# Посмотреть логи
tail -f /root/AIOS/logs/coder_orchestrator.log | grep Balancer

# Метрики
curl -s http://127.0.0.1:9101/metrics | grep balancer
```

## Автоматическая очистка мертвых ключей

Балансировщик v2.1 уже автоматически помечает мертвые ключи:
- 402 Payment Required -> 24h cooldown + permanently_dead после 3 ошибок
- 429 Rate Limited -> exponential backoff 60*2^errors

Но лучше вручную удалить мертвые OpenRouter ключи из JSON и заменить свежими.

## Следующие шаги

После добавления новых ключей:
- Перезапустить `systemctl restart aios-auto-coder`
- Подождать 1 цикл (180с)
- Проверить `tail /root/AIOS/logs/coder_orchestrator.log | grep OK`
- Должно быть `OK: groq/llama-3.3...` или `OK: cerebras/...` или `OK: github/...`
- Метрики: `aios_balancer_errors_total` должен упасть, `requests_total` вырасти
