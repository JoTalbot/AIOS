# AI improvement proposal — policy-engine

Model: qwen2.5:1.5b
Date: 2026-07-04T18:07:53.954277+00:00

### Policy Engine

#### Возможности
- **Правила в YAML/JSON**
  - **Условия**: режим (development_mode), нагрузка, тип ноды (free-tier / third-party), время суток, consent status
  - **Действия**: require, prefer, forbid, scale, move
  - **Приоритет политик**
  - **Аудит и объяснение решений**

#### Примеры правил
- development_mode:
    when: mode == "development"
    action: stop heavy_models whisper_large vector_full
- gpu_preference:
    when: has_gpu
    prefer: inference_tasks
- cost_optimization:
    when: node_type == "free_tier" and load > 70%
    action: migrate_to_low_load_node

#### Интеграция
- **dynamic-tool-orchestrator** (основной потребитель)
- **resource-demand-evaluator**
- **load-aware-scheduler**
- **consent-orchestrator** (перед применением)

#### Алгоритм
1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
2.
