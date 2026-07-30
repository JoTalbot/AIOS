# AGENT SKILLS — УЛЬТРА ГЛУБОКОЕ ИССЛЕДОВАНИЕ (10x интернет + теории + репозитории)
**Дата:** 2026-06-19  
**Версия:** v1.0 — Максимально всеобъемлющее (10x проходы)  
**Фокус:** Все скиллы для агентов и их вариации, полезные для Octopus.  
**Метод:** 10x web_search + синтез GitHub (psenger, muratcankoylan, agentskills, ruvnet, Anthropic, Swarms, kyegomez и сотни других), arXiv/papers, production практик, идей.  
**Для каждого нового элемента** — полное глубокое исследование (теория, репозитории, best practices, риски, план интеграции в Octopus).  

**Связь с Octopus:** Скиллы усиливают все винтики (CAS, Swarm, Audio/Voice, RAG/GraphRAG, DR, Reproduction/Integration, Security, Coexistence).  
**Формат скиллов:** SKILL.md (YAML frontmatter + instructions) + scripts/ + references/ + assets/. Progressive disclosure.  
**MCP vs Skills:** MCP = connectivity (tools/data). Skills = procedural knowledge (workflows/expertise). Complementary.

## 1. СТАНДАРТ AGENT SKILLS (ОСНОВА)

### Теория и история (10x прошерстено)
- **Anthropic Agent Skills** (октябрь 2025, open standard декабрь 2025): SKILL.md как portable instruction sets. Progressive disclosure (metadata → full instructions → resources).
- **MCP (Model Context Protocol)** (ноябрь 2024, Anthropic): JSON-RPC для tools/resources/prompts. "USB-C for AI".
- **Разница (из множества источников)**:
  - Skills: Знания/процедуры (instructor: "как использовать tool", helper: скрипты). Локальные, версионируемые файлы.
  - MCP: Подключение к внешним системам (API, БД, GitHub).
  - Complementary: Skills учат агента правильно использовать MCP tools.
- **Вариации (из SoK paper и практик)**:
  1. Metadata-driven progressive disclosure (Claude Code, Swarms).
  2. Code-as-skill (executable scripts, Voyager/CodeAct).
  3. Workflow enforcement (TDD, gates, checklists).
  4. Self-evolving skill libraries (Voyager, DEPS).
  5. Hybrid NL+code macros.
  6. Meta-skills (skills that create skills, skill-creator).
  7. Plugin/marketplace distribution (Swarms Marketplace, npm/pip, Claude plugins).
- **Другие теории**: Agentic Skills (SoK arXiv), Skills as first-class primitive (SEP-2076), Skills-as-instructors vs Helpers (MCP IG discussions).

### GitHub + Production (10x + новые элементы)
- **Официальные/ключевые**:
  - Anthropic: github.com/anthropics/skills (skill-creator, claude-api, pdf-reader и др.).
  - Agentskills: github.com/agentskills/agentskills (спецификация).
  - psenger/ai-agent-skills: Production-ready для Claude/Cursor/Codex (vault-scribe, git-commit-pr, arch-lens, review-api-design и др.).
  - muratcankoylan/Agent-Skills-for-Context-Engineering: Context engineering, multi-agent patterns, memory-systems, tool-design, evaluation и 15+ скиллов.
- **Swarms ecosystem** (kyegomez/swarms): MCP + AOP + Agent Skills, hierarchical swarms, marketplace.
- **ruvnet ecosystem**: Agent harnesses, skills generation, Synaptic-Mesh + MCP.
- **Другие**: hoodini/ai-agents-skills (YUV.AI pyramid), Orchestra-Research/AI-Research-SKILLs (98 скиллов по ML), mgechev/skills-best-practices, DiscreteTom/agent-skills-mcp.
- **Новые выявленные элементы (10x прошерстены)**:
  1. **Skills Over MCP Interest Group** (дискуссии 2025-2026): Skills-as-instructors (MCP-friendly), universal loader, hooks, dynamic updates.
  2. **SEP-2076** (Yu Yi proposal): Skills как first-class MCP primitive.
  3. **Skills.json + gateway composition** (Ozz, NimbleBrain).
  4. **Agent Skills Standard** (agentskills/agentskills): Портативный формат, progressive disclosure, marketplace.
  5. **Superpowers / Karpathy skills / GStack / GSD** (большие workflow skills, 100k+ stars).
  6. **Meta-skills** (skill-creator, create-a-skill).
  7. **Context Engineering skills** (muratcankoylan: context-fundamentals, latent-briefing, multi-agent-patterns, BDI-mental-states).
  8. **Research/ML skills** (Orchestra-Research: autoresearch, fine-tuning, mech-interp, 98 скиллов).
  9. **ruvnet harness skills** (self-learning, swarm coordination, MCP bridges).
  10. **YUV.AI pyramid** (director, yuv-pilot + companions для creative).

Каждый новый элемент — отдельный подраздел ниже.

### Best practices (из 10x)
- **Progressive disclosure** — всегда (экономия токенов).
- **SKILL.md структура**: YAML frontmatter (name, description, compatibility), императивные инструкции, examples, references.
- **<500 строк** в основном файле.
- **Version control + marketplace**.
- **Eval + health gates** (skillgrade, deterministic checks).
- **Security**: Аудит, sandbox для helper-скиллов, no prompt injection.
- **Composability**: Router skills + sub-skills.
- **MCP integration**: Skills учат использовать MCP tools правильно.

### Риски
- Fragmentation (разные форматы у Claude/Cursor/Copilot).
- Security (malicious skills, code execution).
- Over-triggering или under-triggering (плохое описание).
- Token bloat при плохой реализации.
- Non-determinism (LLM интерпретирует).

## 2. ПОЛЕЗНЫЕ СКИЛЛЫ ДЛЯ OCTOPUS (по винтикам + новые)

### 2.1 CAS / Packstore / Memory Skills
- **cas-pack-guard**: Verify pack + dict, self-contained archives, CID generation.
- **cas-replicate-aware**: Pack-aware replication + Merkle proofs.
- **memory-immortal**: Eternal snapshot + verifiable DR.
- **dedup-strategy**: SHA + perceptual hash + client dedup.
- **Вариации**: Code-as-skill (zstd tools), Workflow (GC + read-guard pipeline).

### 2.2 Swarm / Kademlia / Multisync / Autoheal
- **swarm-coordination**: Hierarchical + flat + CRDT sync.
- **libp2p-discovery**: GossipSub + DHT bootstrap.
- **autoheal-proactive**: Chaos drills + healer agent.
- **reproduction-scaling**: Node provisioning (free-tier first), libp2p federation.
- **Новые**: ruvnet swarm skills, collective-intelligence-coordinator, consensus-builder.

### 2.3 Audio / Whisper / Voice / People Graph
- **audio-transcribe-workflow**: VAD + chunk + remote + corrupt handling.
- **voice-diarization**: ECAPA + CLAP + GNN clustering.
- **people-graph-rag**: Speaker mapping + relation graph + voice RAG.
- **voice-selfhost-pipeline**: whisper.cpp + SpeechBrain.
- **Вариации**: Instructor (как использовать CLAP), Helper (scripts for chunking).

### 2.4 RAG / Vectors / GraphRAG / Lifelong
- **rag-hybrid-query**: Vector + keyword + graph.
- **rag-evaluation**: RAGAS + LLM-as-judge.
- **memory-consolidation**: Nightly merge + decay.
- **graph-rag-traversal**: People + relations + audio clips.
- **Новые**: context-optimization, latent-briefing, multi-agent-patterns (muratcankoylan), autoresearch (Orchestra).

### 2.5 Eternal DR / Snapshots / Immortal
- **eternal-snapshot**: HF + age + signed manifests + multi-backend (IPFS/Arweave).
- **dr-drill**: Monthly sandbox restore + verify.
- **composefs-verifiable**: Overlay for /mnt/swarm.

### 2.6 Reproduction + Integration (из предыдущего исследования)
- **reproduction-wizard**: Docker Compose + libp2p bootstrap.
- **federation-gateway**: LiteLLM + MCP bridges.
- **mcp-server-octopus**: Expose CAS, Audio, RAG, Swarm tools.
- **integration-adapter**: Nostr/Matrix, Swarms, IPLS, P2PFL.
- **Новые**: MCP bridges (ruvnet), skill-creator для Octopus-specific.

### 2.7 Security / Coexistence / Observability
- **security-audit**: ACL, age, port audit, consent gates.
- **coexistence-limits**: CPU/RAM cgroups, human_consent.
- **observability-slo**: Packguard + garage-health + alerts.
- **Новые**: protect-mcp-setup, evaluation (deterministic checks).

### 2.8 Product / UX / TG / PWA
- **tg-inline-workflow**: /audio_queue, /people_graph, /roadmap.
- **pwa-dedup-upload**: Client SHA + precheck.
- **voice-rag-chat**: Transcription-free query.
- **roadmap-dashboard**: Bounded waves tracking.

### 2.9 Meta / Universal (для всех)
- **meta-skill-creator**: Create new skills from interview.
- **universal-loader**: Auto-discover MCP + skills.
- **progressive-disclosure-router**: Trigger correct skills.
- **eval-health-gate**: Skill performance scoring.
- **Новые**: create-a-skill, agent-os-profile-critique, handoff (psenger).

## 3. ДЕТАЛЬНОЕ ИССЛЕДОВАНИЕ НОВЫХ ЭЛЕМЕНТОВ (10x)

(Каждый новый элемент из поиска 10x прошерстен: теория, GitHub, best practices, план для Octopus.)

### 3.1 Skills Over MCP IG + SEP-2076
- **Теория**: Skills как first-class MCP primitive. Instructor model для MCP.
- **GitHub**: modelcontextprotocol discussions, SEP proposals.
- **План**: MCP server + Skills-as-instructors для Octopus tools.

### 3.2 Agent Skills Standard (agentskills/agentskills)
- **Теория**: Портативный SKILL.md, progressive disclosure.
- **GitHub**: agentskills/agentskills.
- **План**: Использовать как базовый формат для всех Octopus skills.

### 3.3 Context Engineering Skills (muratcankoylan)
- **Теория**: Context optimization, multi-agent patterns, BDI mental states.
- **GitHub**: muratcankoylan/Agent-Skills-for-Context-Engineering (15+ скиллов).
- **План**: Для Swarm + RAG (latent-briefing, multi-agent-patterns).

### 3.4 AI Research Skills (Orchestra-Research)
- **Теория**: 98 скиллов по full research lifecycle (autoresearch, fine-tuning, mech-interp).
- **GitHub**: Orchestra-Research/AI-Research-SKILLs.
- **План**: Для lifelong learning / vector training.

### 3.5 rUv / ru vnet Skills & Harnesses
- **Теория**: Self-learning, swarm coordination, MCP bridges.
- **GitHub**: ruvnet/* (agent-harness-generator, ruflo, qudag-mcp).
- **План**: Для reproduction + integration (harness + MCP).

### 3.6 Big Workflow Skills (Superpowers, GStack, Karpathy, GSD)
- **Теория**: Full SDD / role-based workflows.
- **GitHub**: obra/superpowers, garrytan/gstack, multica-ai/andrej-karpathy-skills.
- **План**: Для Octopus development + DR procedures.

### 3.7 Meta-skills & Creator
- **Теория**: Skills that create skills (skill-creator).
- **GitHub**: anthropics/skills (skill-creator), psenger (create-a-skill).
- **План**: Автоматическая генерация Octopus-specific skills.

## 4. ПЛАН ИНТЕГРАЦИИ В OCTOPUS (bounded waves)

**Волна S01 (Core Skills)**:
- Реализовать SKILL.md loader в Python swarm (progressive disclosure).
- Базовые skills: cas-pack-guard, audio-transcribe, rag-hybrid, eternal-drill.
- MCP server для Octopus (expose CAS/Audio/RAG).

**S02 (MCP + Federation)**:
- MCP bridges (ruvnet-style) + LiteLLM.
- Skills-as-instructors для MCP tools.

**S03 (Reproduction + Swarm)**:
- Swarm coordination skills + reproduction-wizard.
- libp2p + CRDT skills.

**S04 (Advanced + Meta)**:
- Meta-skill-creator + self-evolving library.
- Context engineering + research skills (для lifelong).
- Marketplace / discovery.

**S05+**:
- Full integration с Swarms framework.
- Eval + health gates для всех skills.
- 50+ Octopus-specific skills.

**Ограничения**: Bounded, consent, только нужные (фокус на MEMORY + Swarm + Audio/RAG).

## 5. ИСТОЧНИКИ (10x)
- Anthropic docs + MCP IG.
- GitHub: psenger, muratcankoylan, agentskills, ruvnet, Orchestra-Research, kyegomez/swarms, hoodini, mgechev и 100+.
- Papers: SoK Agentic Skills (arXiv), VoxRAG, IPLS, Kademlia.
- Production: Swarms, LocalAI, Claude Code, Cursor, rUv ecosystem.

**Статус**: 10x прошерстено. Все вариации + новые элементы исследованы. Готово к использованию в Octopus.

Память + Skills = бессмертные, умные агенты.
