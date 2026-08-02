#!/usr/bin/env python3
"""Проверка интеграции AGENTS.md (v3.4) без вызова LLM.

Запуск на сервере: /opt/aios/.venv/bin/python scripts/test_agents_md.py
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, "/root/AIOS")

ok = 0
total = 4

# 1) AutocoderV3._load_agents_md читает файл
from aios_core.autocoder_v3 import AutocoderV3

coder = AutocoderV3.__new__(AutocoderV3)
coder.repo_path = Path("/root/AIOS")
md = AutocoderV3._load_agents_md(coder)
assert md and "Protected" in md and "Золотые правила" in md, "AGENTS.md не загружен"
print(f"[1/4] AutocoderV3._load_agents_md OK ({len(md)} символов)")
ok += 1

# 2) AGENTS.md реально попадает в промпт generate_with_rag (LLM замокан)
captured = []

class FakeRAG:
    def get_context_for_task(self, *a, **k):
        return "RAGCTX"

class FakeMemory:
    def get_context_prompt(self, *a, **k):
        return "MEMCTX"
    def get_best_provider(self):
        return "groq"
    def record_failure(self, *a, **k):
        pass
    def record_success(self, *a, **k):
        pass

class FakeBalancer:
    def chat(self, messages, **kwargs):
        captured.append(messages[0]["content"])
        return "⚠️ mock: no real call"

coder.rag = FakeRAG()
coder.memory = FakeMemory()
coder.balancer = FakeBalancer()
coder.pr_creator = None
coder._indexed = True
coder.agents_md = md

res = coder.generate_with_rag(
    "тестовая задача", "aios_core/storage.py", "добавь docstring",
    current_content="def f():\n    pass\n",
)
assert captured, "LLM chat не был вызван"
prompt = captured[0]
assert "AGENTS.md" in prompt and "Золотые правила" in prompt, "AGENTS.md не попал в промпт"
assert "SEARCH" in prompt and "REPLACE" in prompt, "diff-режим не сработал"
assert prompt.index("AGENTS.md") < prompt.index("MEMCTX"), "AGENTS.md должен идти первым"
print("[2/4] AGENTS.md в промпте генерации OK (первым блоком, diff-режим сохранён)")
ok += 1

# 3) Оркестратор: _load_agents_md
import importlib.util
spec = importlib.util.spec_from_file_location("rco", "/root/AIOS/run_coder_orchestrator.py")
rco = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rco)
md2 = rco._load_agents_md()
assert md2 and "Protected" in md2, "оркестратор не загрузил AGENTS.md"
print(f"[3/4] run_coder_orchestrator._load_agents_md OK ({len(md2)} символов)")
ok += 1

# 4) Оркестратор: _is_protected_file через канонический self_protection
assert rco._is_protected_file("aios_core/llm_balancer.py") is True
assert rco._is_protected_file("run_telegram_bot.py") is True
assert rco._is_protected_file("octopus_core/api_v2_batch.py") is True
assert rco._is_protected_file("aios_core/storage.py") is False
assert rco._is_protected_file("aios_core/code_rag.py") is True
print("[4/4] _is_protected_file: protected отфильтровываются, обычные пропускаются OK")
ok += 1

print(f"\n✅ ВСЕ ПРОВЕРКИ ПРОШЛИ: {ok}/{total}")
