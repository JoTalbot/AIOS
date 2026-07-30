# AI improvement proposal — development-mode-guard

Model: qwen2.5:1.5b
Date: 2026-06-27T16:15:34.531459+00:00

### Активация

"Включи development mode"
"Переведи все ноды в режим разработки"
"Останови все модели и тяжёлые сервисы"

### Что делает

1. Запрашивает у resource-demand-evaluator текущий demand.
2. Просит dynamic-tool-orchestrator выключить всё, что имеет низкий/нулевой demand.
3. Через script-deployer останавливает:
   - Ollama / большие модели
   - Whisper workers (кроме минимально необходимых)
   - Vector search / GraphRAG (если не нужны)
   - Любые фоновые тяжёлые процессы.
4. Оставляет только core: loader, health, MCP, consent, basic swarm.
5. При выходе из режима — возвращает всё обратно (с consent).

### Преимущества

- Экономия ресурсов на бесплатных нодах
- Меньше шума во время разработки
- Быстрый переключатель одним сообщением

### Алгоритм

1. Загрузить `SKILL.md`, контекст
