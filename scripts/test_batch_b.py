#!/usr/bin/env python3
"""Проверка Батча B (п.3/п.7): RepoMap-lite + оконная подача + coder-model env.

Запуск: /opt/aios/.venv/bin/python scripts/test_batch_b.py
"""
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, "/root/AIOS")
ok = 0

# 1) RepoMap: собирается, кэшируется, сводка компактная
from aios_core.repomap import build, map_summary

m = build(force=True)
assert m and any(k.startswith("aios_core/") for k in m), "repomap пуст"
assert "aios_core/llm_balancer.py" in m and any("LLMBalancer" in s for s in m["aios_core/llm_balancer.py"])
s = map_summary(1400)
assert 100 < len(s) <= 1450, f"summary len={len(s)}"
m2 = build()  # из кэша
assert m2 == m, "кэш repomap не совпал"
print(f"[1/4] RepoMap: {len(m)} модулей, сводка {len(s)} символов, кэш OK")
ok += 1

# 2) Окна: маленький файл отдаётся целиком
from aios_core.autocoder_v3 import AutocoderV3

coder = AutocoderV3.__new__(AutocoderV3)
small = "def f():\n    pass\n"
assert coder._window_file(small, "task") == small
print("[2/4] _window_file: маленький файл — целиком")
ok += 1

# 3) Окна: большой файл — outline + релевантные функции, в пределах бюджета
big_parts = []
for i in range(40):
    big_parts.append(
        f"def func_{i:02d}(x):\n"
        f'    """Обработка номер {i}."""\n'
        f"    return x + {i}\n\n"
        + "    # filler\n" * 55
    )
big_parts.append(
    "def validate_signature(payload, secret):\n"
    '    """Проверка HMAC-подписи batch-запроса."""\n'
    "    import hmac, hashlib\n"
    "    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()\n"
    + "    # filler\n" * 55
)
big = "\n".join(big_parts)
assert len(big) > 15000
view = coder._window_file(big, "исправь проверку подписи batch-запроса validate_signature")
assert "OUTLINE" in view and "validate_signature" in view, str(view[:400])
assert "hmac.new" in view, "релевантная функция не попала в окно"
assert len(view) <= 13000 + 200, f"бюджет превышен: {len(view)}"
assert "func_39" not in view or len(view) < len(big) * 0.9, "тащит лишнее"
print(f"[3/4] _window_file: большой файл {len(big)} -> окно {len(view)}, целевая функция захвачена")
ok += 1

# 4) AIOS_CODER_MODEL: env-оверрайд модели кодера
captured = []
coder.repo_path = Path("/root/AIOS")
coder.rag = types.SimpleNamespace(get_context_for_task=lambda *a, **k: "")
coder.memory = types.SimpleNamespace(get_context_prompt=lambda *a, **k: "",
                                     get_best_provider=lambda: "groq",
                                     record_failure=lambda *a, **k: None)
class FakeBal:
    def chat(self, msgs, model=None, **kw):
        captured.append(model)
        return "⚠️ mock"
coder.balancer = FakeBal()
coder.pr_creator = None
coder._indexed = True
coder.agents_md = ""
os.environ["AIOS_CODER_MODEL"] = "my-heavy-model"
coder.generate_with_rag("t", "aios_core/storage.py", "i", current_content="def f():\n    pass\n")
assert captured and all(m == "my-heavy-model" for m in captured), captured[:3]
del os.environ["AIOS_CODER_MODEL"]
print("[4/4] AIOS_CODER_MODEL: оверрайд модели кодера работает")
ok += 1

print(f"\n✅ Батч B: {ok}/4 проверок пройдено")
