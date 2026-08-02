"""E2E-тест LLMBalancer v2.2: local-fallback, cohere-fix, нормальная ротация."""
import os
import sys

sys.path.insert(0, "/root/AIOS" if os.path.exists("/root/AIOS") else "/app")

from aios_core.llm_balancer import LLMBalancer  # noqa: E402

print("=" * 70)
print("ТЕСТ 1: ВСЕ ОБЛАКА МЁРТВЫ -> должен сработать LOCAL fallback")
print("=" * 70)
b = LLMBalancer()
local = b.providers.get("local")
print(f"local-зарегистрирован: {local is not None}, модели: {local.models if local else '-'}")
killed = 0
for name, prov in b.providers.items():
    if name != "local":
        for k in prov.keys:
            k.permanently_dead = True
            killed += 1
print(f"убито облачных ключей: {killed}")
ans = b.chat(
    [{"role": "user", "content": "Ответь одним коротким предложением: ты локальная модель?"}],
    max_tokens=40,
    task_type="chat",
)
print(f"ОТВЕТ: {ans[:300]}")
ok1 = bool(ans) and "недоступн" not in ans
print("ТЕСТ 1:", "✅ PASS — local спас" if ok1 else "❌ FAIL")

print()
print("=" * 70)
print("ТЕСТ 2: нормальный режим -> облачный провайдер отвечает")
print("=" * 70)
b2 = LLMBalancer()
ans2 = b2.chat([{"role": "user", "content": "Say OK"}], max_tokens=10, task_type="chat")
print(f"ОТВЕТ: {ans2[:150]}")
ok2 = bool(ans2) and "недоступн" not in ans2
print("ТЕСТ 2:", "✅ PASS" if ok2 else "❌ FAIL")

print()
print("=" * 70)
print("ТЕСТ 3: cohere-fix (формат v2)")
print("=" * 70)
b3 = LLMBalancer()
if "cohere" in b3.providers:
    ans3 = b3.chat([{"role": "user", "content": "Say OK"}], model="command-r7b-12-2024", max_tokens=10, task_type="general")
    print(f"ОТВЕТ: {ans3[:150]}")
    ok3 = bool(ans3) and "недоступн" not in ans3
else:
    print("cohere не зарегистрирован")
    ok3 = False
print("ТЕСТ 3:", "✅ PASS — cohere работает" if ok3 else "❌ FAIL")

print()
print("=" * 70)
print(f"ИТОГ: {sum([ok1, ok2, ok3])}/3 тестов пройдено")
print("=" * 70)
