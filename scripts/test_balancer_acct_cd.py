#!/usr/bin/env python3
"""Юнит-тест аккаунт-куulдауна балансера (v2.4) без сети.

Запуск: /opt/aios/.venv/bin/python scripts/test_balancer_acct_cd.py
"""
import sys
import time

sys.path.insert(0, "/root/AIOS")
from aios_core.llm_balancer import Provider, APIKey

# groq-сценарий: 4 ключа одного аккаунта, все получают 429
p = Provider(name="groq", base_url="http://x",
             keys=[APIKey(key=f"k{i}", provider="groq") for i in range(4)],
             models=["m"])
assert p.get_next_key() is not None, "свежий провайдер должен давать ключ"

for i, k in enumerate(p.keys):
    p.mark_key_error(k, "HTTP 429 Rate Limited")

assert p.account_cooldown_until > time.time(), "аккаунт-куulдаun не выставлен"
assert p.get_next_key() is None, "ключ не должен выдаваться при аккаунт-куulдаunе"
print("✅ [1/2] после 4x429 аккаунт-куulдаun активен, провайдер пропускается")

# одиночный 429 не должен блокировать провайдер целиком (остались живые ключи)
p2 = Provider(name="mistral", base_url="http://x",
              keys=[APIKey(key="a", provider="mistral"), APIKey(key="b", provider="mistral")],
              models=["m"])
p2.mark_key_error(p2.keys[0], "HTTP 429 Rate Limited")
assert p2.account_cooldown_until < time.time(), "ложный аккаунт-куulдаun при живых ключах"
assert p2.get_next_key() is not None, "живой ключ должен выдаваться"
print("✅ [2/2] частичный 429 не блокирует провайдера — живые ключи работают")

print("\n✅ Балансер v2.4: аккаунт-куulдаun работает")
