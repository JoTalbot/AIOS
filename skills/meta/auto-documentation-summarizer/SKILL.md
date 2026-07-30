---
name: auto-documentation-summarizer
version: 1.0
description: Автоматическая суммаризация описаний продуктов и документации
triggers: [documentation_update, new_content]
dependencies: []
llm_required: true
mcp_tools: []
---

```markdown
# Auto-Document Summarizer Skill

## Описание

Этот скил предназначен для...

---

### Overview:
This skill automates the summarization of product descriptions, providing concise summaries that highlight key features and benefits.

### How It Works:
1. **Text Input**: The user inputs detailed information about a product.
2. **Summarization Engine**: Utilizes advanced natural language processing techniques to extract essential details.
3. **Output Generation**: Provides a summarized version of the input text, highlighting important points with additional context where relevant.

---

### Integration Points:

- **App Integration**:
  - This skill integrates seamlessly into various e-commerce apps by automating product descriptions and summaries.

- **User Interface**:
  - Offers a user-friendly interface for direct interaction with the summarization process.

---

### Benefits:

- **Improved Product Visibility**: Summarized products enhance visibility, making them easier to navigate in search results.
- **Increased Conversions**: Short, informative summaries can boost click-through rates and conversions by highlighting key features immediately.
- **Reduced Search Time**: Automating product descriptions speeds up user searches by providing relevant summary information quickly.

---

### Next Steps:
If you're interested in implementing this skill, feel free to reach out. Our team will guide you through setting it up within your existing app infrastructure or help with setup for a new project.

- [Connect with our support](#) to get started.
```

## Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2. Классифицировать навык по тегам (health/api/memory/disk/telegram/systemd/docker/security/ai).
3. Выполнить только безопасные read-only проверки через `code/run.py` и общий `generic_skill_runtime`.
4. Сформировать JSON-отчёт: статус, найденные факты, риски, рекомендации, следующий bounded-шаг.
5. Если требуется изменение системы — записать proposal/rollback в logs/reports и ждать consent gate либо выполнения автономным агентом в bounded-режиме.
6. Для Telegram: прямые push-уведомления запрещены, кроме `skill-notification` и отчётов автономного агента.
7. Для AWS/платных ресурсов: только аудит; создание/включение ресурсов запрещено без явной команды человека.

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Мониторинг: `scripts/skill_evolution_cycle.py` пересчитывает health/coverage и дописывает AI-предложения в `references/`.
- Развитие через ИИ: локальный Ollama/Qwen генерирует bounded improvement proposal; автоприменяются только безопасные структурные улучшения (алгоритм, тест, runtime wrapper).
- Описание назначения: Операционный навык Octopus: auto-documentation-summarizer.
