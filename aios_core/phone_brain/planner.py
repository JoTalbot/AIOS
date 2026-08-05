"""LLM-планировщик Phone Brain (этап 3): цель на русском → цепочка skills.

Цель владельца («предупреди маму в WhatsApp, что задержусь») разбирается
LLM на последовательность декларативных skills из skills/phone/ с параметрами.
Исполнение — через SkillEngine, каждый шаг остаётся тraceable, статистика
селекторов продолжает копиться.

Текстовые вызовы идут через существующий LLMBalancer (защищённый — только импорт,
без изменений). В тестах chat-функция подменяется.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Callable

_BALANCER: Any = None
_BALANCER_LOCK = threading.Lock()

_SYSTEM_PROMPT = """Ты — планировщик действий на Android-телефоне владельца (система AIOS Phone Brain).
По цели владельца собери план из доступных сценариев (skills).

Ответ — СТРОГО валидный JSON без пояснений и markdown:
{"plan": [{"skill": "<id>", "params": {...}}, ...]}
или, если цель нельзя выполнить известными сценариями:
{"error": "<краткая причина по-русски>"}

Правила:
- используй только skills из списка, ровно их id;
- заполняй ВСЕ объявленные params каждого выбранного skill;
- не более @MAX_STEPS@ шагов;
- params — только строки; длина текста сообщения ≤ 500 символов;
- не выдумывай новые сценарии и параметры."""


def _system_prompt(max_steps: int) -> str:
    # .format нельзя: в промпте есть JSON-пример с фигурными скобками
    return _SYSTEM_PROMPT.replace("@MAX_STEPS@", str(max_steps))


def _balancer_chat():
    """Ленивый синглтон LLMBalancer (конструктор читает ключи из env/файла)."""
    global _BALANCER
    with _BALANCER_LOCK:
        if _BALANCER is None:
            from aios_core.llm_balancer import LLMBalancer
            _BALANCER = LLMBalancer()
        return _BALANCER.chat


def _extract_json(text: str) -> dict | None:
    start = str(text or "").find("{")
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(text[start:index + 1])
                    return data if isinstance(data, dict) else None
                except ValueError:
                    return None
    return None


class PhonePlanner:
    """Строит и выполняет планы из skills по цели на естественном языке."""

    def __init__(self, engine: Any, chat: Callable | None = None, max_steps: int = 3):
        self.engine = engine
        self._chat_injected = chat
        self.max_steps = max(1, int(max_steps))

    # -------------------------------------------------------------- LLM

    def _catalog(self) -> list[dict]:
        catalog = []
        available_apps = None
        gateway = getattr(self.engine, "gateway", None)
        if gateway is not None:
            try:
                profiles = gateway.app_profiles().get("profiles") or []
                available_apps = {str(p.get("id")) for p in profiles if p.get("available")}
            except Exception:
                available_apps = None
        for skill in self.engine.list():
            if not skill.get("id"):
                continue  # битые skill-файлы в планировщик не попадают
            # Скилл для неустановленного приложения заведомо невыполним.
            if available_apps is not None and str(skill.get("app") or "") not in available_apps:
                continue
            full = self.engine.get(skill["id"]) or {}
            catalog.append({"id": skill["id"], "title": skill["title"],
                            "app": skill["app"], "params": full.get("params") or [],
                            "sensitive": skill["sensitive"]})
        return catalog

    def plan(self, goal: str) -> dict:
        """Возвращает {"status":"ok","plan":[...]} или {"status":"error",...}."""
        goal = str(goal or "").strip()
        if not goal:
            return {"status": "error", "code": "empty_goal", "error": "Пустая цель"}
        chat = self._chat_injected or _balancer_chat()
        prompt = ("Доступные сценарии (JSON):\n" + json.dumps(self._catalog(), ensure_ascii=False)
                  + "\n\nЦель владельца: " + goal[:500])
        try:
            raw = chat([{"role": "user", "content": prompt}],
                       system=_system_prompt(self.max_steps),
                       max_tokens=900, temperature=0.15, task_type="planning")
        except Exception as exc:
            return {"status": "error", "code": "llm_unavailable", "error": str(exc)[:200]}
        data = _extract_json(raw or "")
        if data is None:
            # один исправляющий запрос — модели любят markdown-ограждения
            try:
                raw2 = chat([{"role": "user", "content":
                              prompt + "\n\nОтветь ТОЛЬКО JSON-объектом, без ```."}],
                            system=_system_prompt(self.max_steps),
                            max_tokens=900, temperature=0.0, task_type="planning")
                data = _extract_json(raw2 or "")
            except Exception:
                data = None
        if data is None:
            return {"status": "error", "code": "llm_bad_json",
                    "error": "LLM не вернула валидный JSON"}
        if data.get("error"):
            return {"status": "error", "code": "planner_refused",
                    "error": str(data.get("error"))[:250]}
        return self._validate_plan(data.get("plan"))

    def _validate_plan(self, plan: Any) -> dict:
        if not isinstance(plan, list) or not plan:
            return {"status": "error", "code": "invalid_plan", "error": "Пустой или невалидный план"}
        if len(plan) > self.max_steps:
            return {"status": "error", "code": "invalid_plan",
                    "error": f"План длиннее {self.max_steps} шагов"}
        steps: list[dict] = []
        for index, item in enumerate(plan):
            if not isinstance(item, dict):
                return {"status": "error", "code": "invalid_plan", "error": f"шаг {index} не объект"}
            skill_id = str(item.get("skill") or "").strip()
            skill = self.engine.get(skill_id)
            if skill is None:
                return {"status": "error", "code": "unknown_skill",
                        "error": f"Неизвестный skill '{skill_id}'"}
            params = item.get("params") or {}
            if not isinstance(params, dict) or any(not isinstance(v, (str, int, float)) for v in params.values()):
                return {"status": "error", "code": "invalid_params",
                        "error": f"шаг {index}: params должны быть строками/числами"}
            declared = [str(p) for p in (skill.get("params") or [])]
            missing = [name for name in declared if name not in params or str(params[name]).strip() == ""]
            if missing:
                return {"status": "error", "code": "missing_param",
                        "error": f"skill '{skill_id}': нет параметров {', '.join(missing)}"}
            steps.append({"skill": skill_id, "title": skill["title"],
                          "params": {str(k): str(v)[:500] for k, v in params.items()}})
        return {"status": "ok", "plan": steps}

    # ---------------------------------------------------------------- run

    def run(self, goal: str) -> dict:
        """Планирует и последовательно выполняет skills через SkillEngine."""
        planned = self.plan(goal)
        if planned.get("status") != "ok":
            return planned
        executed: list[dict] = []
        for step in planned["plan"]:
            result = self.engine.run(step["skill"], params=step["params"])
            executed.append({"skill": step["skill"], "title": step["title"],
                             "ok": result.get("status") == "ok",
                             "duration_seconds": result.get("duration_seconds"),
                             **({"step_failed": result.get("step"), "error": result.get("error")}
                                if result.get("status") != "ok" else {})})
            if result.get("status") != "ok":
                return {"status": "error", "code": str(result.get("code") or "step_failed"),
                        "error": f"{step['skill']}: {result.get('error')}"[:250],
                        "plan": planned["plan"], "executed": executed}
        return {"status": "ok", "goal": str(goal)[:200], "plan": planned["plan"],
                "executed": executed}
