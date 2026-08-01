# Как развернуть локальный LLM-кодер на Hetzner

## Зачем
Локальная модель (Qwen2.5-Coder) = код не уходит в облако, полная автономия,
нет rate-limits. Для конфиденциальности это единственный вариант.

## 1. Заказать сервер (вы делаете в панели Hetzner)

**Рекомендация: Hetzner Cloud GPU — «GEX44»**
- GPU: **RTX 4000 Ada 20 GB VRAM**
- CPU: 14 vCPU, RAM: 64 GB
- ~€184/мес (после июньских подорожаний 2026 — проверьте актуальную цену)

Или **GEX31** (RTX 4000 SFF Ada 20GB) если доступен дешевле.

> Заказывается в **Hetzner Cloud Console → Create Server → GPU**.
> После создания сервер будет с SSH. Перенесите туда AIOS (git clone) и свой SSH-ключ.

## 2. Установить (скрипт уже готов)

На новом сервере:
```bash
# 1) Загрузить AIOS
git clone https://github.com/JoTalbot/AIOS.git /root/AIOS
cd /root/AIOS

# 2) Скопировать секреты с текущего сервера
scp root@167.233.95.7:/etc/aios/aios-auto-coder.env /etc/aios/aios-auto-coder.env

# 3) Поставить Ollama + модели
bash scripts/setup_local_llm_hetzner.sh
```

## 3. Модели

| Модель | Размер (Q4) | Для чего |
|---|---|---|
| `qwen2.5-coder:14b` | ~9 GB | **основная**, лучший открытый кодер |
| `qwen2.5-coder:7b` | ~4.7 GB | быстрые простые правки |
| `qwen2.5-coder:32b` | ~20 GB | впритык в 20GB VRAM, максимум качества |

## 4. Как AIOS использует локальную модель

Балансировщик уже понимает провайдера `local` (Ollama, OpenAI-совместимый).
Он включается автоматически, если:
- в `/etc/aios/aios-auto-coder.env` есть `LOCAL_LLM=1`
- Ollama запущена на `http://localhost:11434`

Тогда `qwen2.5-coder:14b` становится ещё одним провайдером в цепочке
(наряду с Groq/Gemini/Cerebras/OpenRouter). Можно переключить основную
модель кодера на локальную, установив в env:
```
LLM_MODEL=qwen2.5-coder:14b
```
и убрать/оставить API-провайдеры как fallback.

## 5. Перезапуск после настройки
```bash
systemctl restart aios-auto-coder
docker restart aios-api aios-mcp aios-dashboard
```

## 6. Проверка
```bash
cd /root/AIOS && /opt/aios/.venv/bin/python3.11 -c "
from aios_core.llm_balancer import LLMBalancer
b=LLMBalancer()
print('local registered:', 'local' in b.providers)
print(b.chat([{'role':'user','content':'Скажи OK'}], model='qwen2.5-coder:14b', max_tokens=5))
"
```

## ⚠️ Честные ожидания
- Локальная 14B на RTX 4000 (20GB) быстрее, чем на CPU, но **медленнее и слабее**,
  чем бесплатные API (Groq/Cerebras). Для агента-кодера, который зовёт модель часто,
  API обычно удобнее.
- Локальная модель выигрывает только в **конфиденциальности** и **отсутствии лимитов**.
