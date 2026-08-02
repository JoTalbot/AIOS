# AIOS Autocoder v3 - RAG + Memory + Self-Learning + Auto-PR

## Overview
v3 расширяет v2 добавлением:
- **Code RAG**: индексация 810+ функций из aios_core, поиск релевантного кода по TF-IDF + ChromaDB
- **Memory**: persistent память успешных/фейловых фиксов, file stats, provider stats, pattern learning
- **Self-Learning**: best provider, best skill, avoid files, successful patterns
- **Auto-PR**: создание GitHub PR через API (gh CLI или curl)

## Architecture

```
Task -> RAG Context (5 relevant snippets) + Memory Context (best provider, avoid files, recent fixes)
      -> Enhanced Prompt (RAG + Memory + Task)
      -> LLMBalancer (try best provider first: groq -> cerebras -> github)
      -> Generate Code
      -> Apply Fix
      -> Record Success/Failure in Memory
      -> Optional Auto-PR
```

## Modules

### 1. aios_core/code_rag.py (8KB)
- `CodeRAG(repo_path, use_chroma=True)`
- `index_repo(max_files=200)`: парсит Python файлы, извлекает def/class, индексирует в ChromaDB
- `search(query, top_k=5)`: TF-IDF fallback + Chroma query
- `get_context_for_task(description, file)`: возвращает markdown с 5 релевантными сниппетами

**Example:**
```python
rag = CodeRAG(".")
rag.index_repo() # 810 functions indexed
rag.search("fix security vulnerability") # -> [AdvancedSecurity, etc]
rag.get_context_for_task("fix HACK") # -> "# Relevant code context...\n## 1. file:func\n```python..."
```

### 2. aios_core/autocoder_memory.py (6KB)
- Persistent JSON: `data/autocoder_v3_memory.json`
- `record_success(file, desc, instr, code_len, provider, skill)`
- `record_failure(file, desc, error, provider)`
- `get_best_provider()`: highest success rate
- `get_best_skill_for_task(desc)`: based on past successes
- `get_avoid_files()`: files with fails > fixes
- `get_context_prompt(task)`: generates memory context for LLM

### 3. aios_core/autocoder_v3.py (10KB)
- `AutocoderV3(repo_path)`
- `ensure_indexed()`: index 810 functions
- `generate_with_rag(task, file, instruction)`: RAG + Memory + Balancer
- `apply_fix(file, code)`
- `run_task(task, file, instruction, create_pr=False)`: full pipeline
- `AutoPRCreator`: creates branch + push + PR via gh CLI or GitHub API

### 4. run_coder_orchestrator_v3.py (2.6KB)
- Uses v2's phase_analyze, phase_plan, phase_validate, phase_commit
- But uses v3 for CODE phase: RAG + Memory
- Logs to `logs/coder_v3.log`

## RAG Example

Task: "Устранить HACK-решения в octopus_core/api_v2_batch.py"
RAG finds:
- `aios_core/code_refactorer.py:analyze_and_refactor_file` - replaces HACK
- `aios_core/advanced_security.py:AdvancedSecurity` - secure POST
- etc.

Context injected into prompt improves generation quality.

## Memory Example

After 10 successful fixes with groq provider:
- `get_best_provider()` -> "groq" (success rate 90%)
- `get_avoid_files()` -> ["aios_core/bad_file.py"] (3 fails, 0 fixes)
- `get_context_prompt("fix security")` -> "Best provider: groq, Avoid: bad_file.py, Recent fixes: ..."

## Auto-PR

```python
pr_creator = AutoPRCreator()
result = pr_creator.create_branch_and_pr("aios_core/fixed.py", "fix security bug")
# Creates branch auto/v3/fixed-20260802..., commit, push, PR via gh or API
# Returns {ok: True, branch: "...", pr_url: "https://github.com/.../pull/123"}
```

## Service

Systemd: `aios-auto-coder-v3.service`
- Exec: `/opt/aios/.venv/bin/python3.11 -u run_coder_orchestrator_v3.py`
- Logs: `logs/coder_v3.log`
- Env: LLM_MODEL=llama-3.3-70b-versatile

Start:
```bash
systemctl start aios-auto-coder-v3
systemctl status aios-auto-coder-v3
tail -f logs/coder_v3.log
```

## Comparison v2 vs v3

| Feature | v2 | v3 |
|---------|----|----|
| Code search | random file pick from recent | RAG 810 functions TF-IDF + Chroma |
| Memory | backlog lessons 30 | persistent memory 100 successes/fails + patterns + file stats |
| Provider selection | hardcoded priority | learned best provider from memory |
| Skill routing | keyword match | memory-based best skill |
| Auto-PR | commit_only | optional PR creation |
| Context | todos + recent files | RAG 5 snippets + memory + lessons |

## Testing

```bash
pytest tests/test_code_rag.py tests/test_autocoder_memory.py tests/test_autocoder_v3.py -v
# 15 passed
```

## Future Improvements

- Use ChromaDB embeddings (currently TF-IDF fallback, Chroma upsert limited to 100)
- Add vector embeddings via sentence-transformers
- Add self-learning loop: analyze failed attempts, generate new lessons
- Add auto-PR with auto-merge after tests pass
- Add RAG for docs and issues (not just code)

## Files

- aios_core/code_rag.py
- aios_core/autocoder_memory.py
- aios_core/autocoder_v3.py
- run_coder_orchestrator_v3.py
- tests/test_code_rag.py, test_autocoder_memory.py, test_autocoder_v3.py
- /etc/systemd/system/aios-auto-coder-v3.service
- data/autocoder_v3_memory.json (runtime)
