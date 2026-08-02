# Как добавить бесплатные API-ключи внешних LLM

AIOS использует **LLMBalancer** — он сам балансирует между провайдерами и
переключается на следующий ключ/провайдер при ошибке (402/403/429/5xx).

## Поддерживаемые бесплатные провайдеры

| Провайдер | Где взять ключ | Бесплатные модели |
|---|---|---|
| **Google Gemini** | https://aistudio.google.com/apikey | `gemini-2.0-flash`, `gemini-2.5-flash` |
| **Groq** | https://console.groq.com/keys | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` |
| **Cerebras** | https://cloud.cerebras.ai | `llama-3.3-70b`, `llama-3.1-8b` |
| **Mistral** | https://console.mistral.ai | `mistral-small-latest`, `open-mistral-7b` |
| **Cohere** | https://dashboard.cohere.com/api-keys | `command-r`, `command-r7b-12-2024` |
| **Together AI** | https://api.together.ai/settings/api-keys | `Meta-Llama-3-70B-Instruct-Turbo` |
| **OpenRouter (free-модели)** | https://openrouter.ai/settings/keys | `gpt-oss-20b:free`, `gemma-4-31b-it:free` и др. |
| **GitHub Models** | уже настроен (`GITHUB_API_KEY`) | свободные лимиты |

## Как добавить ключ

### Способ 1 — файл JSON `/root/AIOS/data/.llm_keys.json`
```json
{
  "openrouter": ["sk-or-v1-xxx", "sk-or-v1-yyy"],
  "gemini":     ["AIza-xxx", "AIza-yyy"],
  "groq":       ["gsk_xxx"],
  "cerebras":   ["xxx"],
  "mistral":    ["xxx"],
  "cohere":     ["xxx"],
  "together":   ["xxx"]
}
```
Один провайдер = список ключей (для балансировки). После правки **перезапустите** сервисы:
```bash
systemctl restart aios-auto-coder
docker restart aios-api aios-mcp
```

### Способ 2 — env-переменные
В `/etc/aios/aios-auto-coder.env` или `/root/AIOS/.env`:
```bash
GROQ_API_KEY=gsk_xxx
GROQ_API_KEY_2=gsk_yyy
CEREBRAS_API_KEY=xxx
MISTRAL_API_KEY=xxx
COHERE_API_KEY=xxx
TOGETHER_API_KEY=xxx
```
После — перезапустите сервисы (как выше).

## Проверка, что ключ работает
```bash
# Перечислить зарегистрированные провайдеры
cd /root/AIOS && /opt/aios/.venv/bin/python3.11 -c "from aios_core.llm_balancer import LLMBalancer; print(list(LLMBalancer().providers.keys()))"

# Проверить конкретную модель
/opt/aios/.venv/bin/python3.11 - <<'PY'
import os
os.environ["MISTRAL_API_KEY"]="ВАШ_КЛЮЧ"
from aios_core.llm_balancer import LLMBalancer
b=LLMBalancer()
print(b.chat([{"role":"user","content":"Скажи OK"}], model="mistral-small-latest", max_tokens=5))
PY
```

## Советы
- Чем больше провайдеров и ключей — тем стабильнее (балансировщик подхватывает сбой одного).
- Free-tier провайдеры имеют **rate-limits** (429). Балансировщик автоматически делает
  cooldown 60с и пробует следующий ключ/провайдер.
- Для кодовых задач предпочтительны: **OpenRouter free**, **Groq**, **Cerebras**, **Together**, **Mistral**.

## Локальный fallback (Ollama) — добавлено 2026-08-02

Если ВСЕ облачные ключи умерли (402/403/429 у всех провайдеров), LLMBalancer v2.2
автоматически переключается на локальную Ollama (`aios-coder:7b` → `qwen2.5-coder:7b` → `qwen2.5-coder:1.5b`)
вместо ошибки «Все LLM-провайдеры недоступны». Работает и для автокодера, и для чата.

- Хост: `LOCAL_LLM=1` уже стоит в `/etc/aios/aios-auto-coder.env` и `/etc/aios/aios-telegram-bot.env`.
- Docker (aios-api): `LOCAL_LLM=1` + `LOCAL_LLM_BASE_URL=http://172.18.0.1:11434/v1/chat/completions`
  в `docker-compose.prod.yml`; Ollama слушает `0.0.0.0`, наружу закрыта ufw
  (открыт только для docker-подсетей 172.17/172.18).

Проверка всех ключей и fallback:
```bash
/opt/aios/.venv/bin/python scripts/check_llm_keys.py     # реальная проверка всех ключей
/opt/aios/.venv/bin/python scripts/test_balancer_e2e.py  # e2e: clouds-dead -> local, cohere, ротация
```
