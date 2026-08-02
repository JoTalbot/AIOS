# AIOS Autocoder Fix Report v2.1
Date: 2026-08-02

## Проблемы
- Balancer падал в слабую локальную модель 1.5B
- OpenRouter 402, Airforce 429, Groq 404 для gpt-4o-mini
- Бэклог 463 дубликата
- Hallucination путей
- Telegram 400
- Commit без валидации
- Gateway сломан (ToolDefinition не определен)

## Исправления
### Balancer v2.1
- Приоритет groq > deepseek > zai > mistral > cohere > gemini > huggingface > openai > airforce > openrouter > local
- Убран local_first
- 402 -> 24h + dead после 3 ошибок
- 429 -> exponential backoff
- Fallback: llama-3.3-70b-versatile -> llama-3.1-8b -> gemma-3-27b -> qwen2.5-coder:7b
- Cohere v2 формат

### Orchestrator v2
- tg_send retry без HTML при 400
- DEDUP бэклога (40 символов)
- random.choice для файлов
- BLOCKED commit при validation failed

### Новые модули
- tech_debt_reporter.py - JSON отчет TODO/HACK/BUG
- security_audit.py - XSS/secrets/dangerous calls

### Конфиг
- LLM_MODEL=llama-3.3-70b-versatile (Groq)
- Бэклог 463 -> 11
- Gateway восстановлен

## Результат
- Balancer OK groq/llama-3.3-70b с первого раза
- Циклы проходят VALIDATE passed -> commit_only
- Tech debt: 53 TODO, 20 complex, 9 security
- Security audit: 5 XSS, 0 secrets
- API health ok, dashboard 200

## Файлы
- aios_core/llm_balancer.py v2.1
- run_coder_orchestrator.py v2
- tech_debt_reporter.py new
- security_audit.py new
