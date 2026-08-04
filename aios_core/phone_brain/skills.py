"""Skill-движок Phone Brain — декларативные сценарии управления телефоном.

Этап 2 умной архитектуры. Сценарии живут в ``skills/phone/*.yaml|*.json``:

.. code-block:: yaml

    id: whatsapp_open_chat
    title: "WhatsApp: открыть чат"
    confirm: true            # требуется payload.confirm=true (гейт внешнего вызова)
    sensitive: false
    steps:
      - id: open
        do: app.open
        package: com.whatsapp
      - id: find
        do: ui.tap
        timeout: 6
        selectors:           # упорядоченная fallback-цепочка
          - {resource: "com.whatsapp:id/menuitem_search"}
          - {desc_contains: "Поиск"}

Глаголы шагов: app.open, ui.wait, ui.tap, ui.type, ui.key, wait, verify.
В текстах доступна подстановка ``${param}`` из payload.params.

«Умное» поведение: статистика селекторов (data/android_gateway/skill_stats.json)
запоминает, какой вариант цепочки реально сработал, и ставит его первым при
следующих запусках. Когда вся цепочка падает — это сигнал для этапа 3
(LLM/vision-восстановление селекторов).

Приватность: текст экрана читается движком только на сервере; наружу
(результаты, журналы, статистика) выходят только id шагов и типы селекторов.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aios_core.phone_brain.common import iso, read_json, write_json

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:  # pragma: no cover
    _YAML_AVAILABLE = False

VERBS = {"app.open", "ui.wait", "ui.tap", "ui.type", "ui.key", "wait", "verify"}
_MAX_TEXT = 2000


def _fold(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _node_center(node: dict) -> tuple[int, int] | None:
    bounds = node.get("bounds")
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        return None
    try:
        left, top, right, bottom = (int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]))
    except (TypeError, ValueError):
        return None
    if right <= left or bottom <= top:
        return None
    return ((left + right) // 2, (top + bottom) // 2)


def _matches(node: dict, selector: dict) -> bool:
    """Один селектор против одного узла UI-дерева."""
    text = _fold(node.get("text"))
    desc = _fold(node.get("description") or node.get("desc"))
    resource = str(node.get("resource") or node.get("resource_id") or "")
    if "text" in selector:
        if text != _fold(selector.get("text")):
            return False
    if "text_contains" in selector:
        needle = _fold(selector.get("text_contains"))
        if not needle or needle not in text:
            return False
    if "desc" in selector:
        if desc != _fold(selector.get("desc")):
            return False
    if "desc_contains" in selector:
        needle = _fold(selector.get("desc_contains"))
        if not needle or needle not in desc:
            return False
    if "resource" in selector:
        wanted = str(selector.get("resource") or "")
        if not wanted or not (resource == wanted or resource.endswith(wanted)):
            return False
    if "label" in selector:
        needle = _fold(selector.get("label"))
        if not needle or (needle not in text and needle not in desc):
            return False
    if "bounds" in selector:
        bounds = node.get("bounds")
        want = selector.get("bounds")
        if not isinstance(bounds, (list, tuple)) or not isinstance(want, (list, tuple)) or len(want) != 4 or len(bounds) != 4:
            return False
        try:
            if any(abs(int(bounds[i]) - int(want[i])) > 24 for i in range(4)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def _interpolate(value: Any, params: dict) -> Any:
    """Подстановка ${param} в строковых значениях шага/селектора."""
    if isinstance(value, str):
        result = value
        for key, item in params.items():
            result = result.replace("${" + str(key) + "}", str(item))
        if "${" in result:
            missing = result.split("${", 1)[1].split("}", 1)[0]
            raise KeyError(missing)
        return result
    if isinstance(value, dict):
        return {key: _interpolate(item, params) for key, item in value.items()}
    if isinstance(value, list):
        return [_interpolate(item, params) for item in value]
    return value


class SkillValidationError(Exception):
    """Некорректный skill-файл (пропускается при загрузке)."""


class SkillEngine:
    """Загрузка и выполнение декларативных phone-skills."""

    def __init__(self, root: Path | str, gateway: Any = None, events: Any = None,
                 skills_dir: Path | str | None = None, poll_interval: float = 0.7,
                 vision: Any = None):
        self.root = Path(root)
        self.gateway = gateway
        self.events = events
        self.vision = vision
        self.skills_dir = (Path(skills_dir) if skills_dir
                           else self.root / "skills" / "phone")
        self.poll_interval = max(0.2, float(poll_interval))
        self.stats_path = (self.root / "data" / "android_gateway" / "skill_stats.json"
                           if skills_dir is None else self.root / "skill_stats.json")
        self._stats: dict | None = None
        self._skills: dict[str, dict] | None = None
        self.load_errors: list[dict] = []

    # ------------------------------------------------------------ loading

    def _load_file(self, path: Path) -> dict:
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            if not _YAML_AVAILABLE:
                raise SkillValidationError("PyYAML недоступен")
            data = yaml.safe_load(raw)
        else:
            import json
            data = json.loads(raw)
        return self._validate(data, path)

    @staticmethod
    def _validate(data: Any, path: Path) -> dict:
        if not isinstance(data, dict):
            raise SkillValidationError("корень должен быть объектом")
        skill_id = str(data.get("id") or "").strip()
        if not skill_id:
            raise SkillValidationError("нет id")
        steps = data.get("steps")
        if not isinstance(steps, list) or not steps:
            raise SkillValidationError("нет steps")
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or step.get("do") not in VERBS:
                raise SkillValidationError(f"шаг {index}: неизвестный do ({step.get('do') if isinstance(step, dict) else '?'})")
            if step.get("do") in ("ui.wait", "ui.tap") and not step.get("selectors"):
                raise SkillValidationError(f"шаг {index}: нужны selectors")
            if step.get("do") == "verify" and not (step.get("selectors") or step.get("foreground")):
                raise SkillValidationError(f"шаг {index}: verify требует selectors или foreground")
            step.setdefault("id", f"step_{index}")
        return {"id": skill_id, "title": str(data.get("title") or skill_id)[:120],
                "app": str(data.get("app") or "")[:60],
                "params": [str(p) for p in (data.get("params") or [])][:12],
                "confirm": bool(data.get("confirm", True)),
                "sensitive": bool(data.get("sensitive", False)),
                "steps": steps, "file": path.name}

    def _ensure_loaded(self) -> None:
        if self._skills is not None:
            return
        self._skills = {}
        self.load_errors = []
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.iterdir()):
            if path.suffix.lower() not in (".yaml", ".yml", ".json") or not path.is_file():
                continue
            try:
                skill = self._load_file(path)
                self._skills[skill["id"]] = skill
            except Exception as exc:
                self.load_errors.append({"file": path.name, "error": str(exc)[:160]})

    def get(self, skill_id: str) -> dict | None:
        """Возвращает skill по id или None."""
        self._ensure_loaded()
        return self._skills.get(str(skill_id or ""))

    def list(self) -> list[dict]:
        """Метаданные доступных skills (без тел шагов)."""
        self._ensure_loaded()
        items = [{"id": skill["id"], "title": skill["title"], "app": skill["app"],
                  "params": skill.get("params") or [],
                  "confirm": skill["confirm"], "sensitive": skill["sensitive"],
                  "steps": len(skill["steps"]), "file": skill["file"]}
                 for skill in self._skills.values()]
        for error in self.load_errors:
            items.append({"id": "", "title": "⚠️ битый skill-файл", "app": "",
                          "confirm": False, "sensitive": False, "steps": 0,
                          "file": error["file"], "error": error["error"]})
        return items

    def reload(self) -> int:
        """Перечитывает skills с диска (после добавления/правки файлов)."""
        self._skills = None
        self._ensure_loaded()
        return len(self._skills)

    # ------------------------------------------------------------- stats

    def _load_stats(self) -> dict:
        if self._stats is None:
            self._stats = read_json(self.stats_path, {})
        return self._stats

    def _save_stats(self) -> None:
        if self._stats is not None:
            write_json(self.stats_path, self._stats)

    def _ordered_selectors(self, skill_id: str, step_id: str, selectors: list[dict]) -> list[tuple[int, dict]]:
        """Fallback-цепочка с учётом памяти: последний рабочий селектор — первым."""
        indexed = list(enumerate(selectors))
        entry = self._load_stats().get(f"{skill_id}:{step_id}") or {}
        last_good = entry.get("last_good")
        if isinstance(last_good, int) and 0 <= last_good < len(selectors):
            indexed.sort(key=lambda pair: 0 if pair[0] == last_good else 1)
            return indexed
        return indexed

    def _mark(self, skill_id: str, step_id: str, index: int, ok: bool) -> None:
        stats = self._load_stats()
        key = f"{skill_id}:{step_id}"
        entry = stats.get(key) or {"ok": {}, "fail": {}}
        bucket = entry.setdefault("ok" if ok else "fail", {})
        bucket[str(index)] = int(bucket.get(str(index)) or 0) + 1
        if ok and index >= 0:
            entry["last_good"] = index
        entry["updated_at"] = iso()
        stats[key] = entry
        self._save_stats()

    def _learn(self, skill_id: str, step_id: str, x: int, y: int) -> None:
        """Запоминает координаты, подсказанные VLM (этап 3 самовосстановление)."""
        stats = self._load_stats()
        key = f"{skill_id}:{step_id}"
        entry = stats.get(key) or {"ok": {}, "fail": {}}
        entry["learned"] = {"center": [int(x), int(y)], "at": iso()}
        entry["updated_at"] = iso()
        stats[key] = entry
        self._save_stats()

    @staticmethod
    def _find_by_learned(snapshot: dict, center: list) -> dict | None:
        """Ищет живой узел рядом с запомненной VLM-точкой (±90px по Чебышёву)."""
        try:
            cx, cy = int(center[0]), int(center[1])
        except (TypeError, ValueError, IndexError):
            return None
        best: dict | None = None
        best_distance = 90
        for node in snapshot.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node_center = _node_center(node)
            if node_center is None:
                continue
            distance = max(abs(node_center[0] - cx), abs(node_center[1] - cy))
            if distance <= best_distance:
                best, best_distance = node, distance
        return best

    # ------------------------------------------------------------- events

    def _event(self, event_type: str, data: dict) -> None:
        if self.events is not None:
            try:
                self.events.append(event_type, data)
            except Exception:
                pass

    # ------------------------------------------------------------ runtime

    def _snapshot(self) -> dict:
        if self.gateway is None:
            return {"status": "error", "error": "gateway не подключён"}
        try:
            return self.gateway.ui_snapshot(confirm=True, include_text=True)
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:200]}

    def _find(self, selectors: list[dict], snapshot: dict) -> tuple[int, dict] | tuple[None, None]:
        nodes = snapshot.get("nodes") or []
        for index, selector in selectors:
            for node in nodes:
                if isinstance(node, dict) and _matches(node, selector):
                    return index, node
        return None, None

    def _wait_match(self, skill_id: str, step: dict, params: dict,
                    timeout: float) -> dict:
        """Ждёт появления элемента по fallback-цепочке; возвращает результат шага."""
        deadline = time.monotonic() + max(0.0, timeout)
        ordered = self._ordered_selectors(skill_id, str(step["id"]), step["selectors"])
        learned = (self._load_stats().get(f"{skill_id}:{step['id']}") or {}).get("learned")
        while True:
            snapshot = self._snapshot()
            if snapshot.get("status") != "ok":
                return {"ok": False, "code": "ui_unavailable",
                        "error": str(snapshot.get("error") or "UI недоступен")[:200]}
            # Ранее восстановленная VLM точка имеет приоритет над цепочкой.
            if learned and isinstance(learned.get("center"), list):
                node = self._find_by_learned(snapshot, learned["center"])
                if node is not None:
                    self._mark(skill_id, str(step["id"]), -1, True)
                    return {"ok": True, "selector": -1, "node": node, "snapshot": snapshot}
            try:
                resolved = [(index, _interpolate(selector, params)) for index, selector in ordered]
            except KeyError as exc:
                return {"ok": False, "code": "missing_param",
                        "error": f"нет параметра ${{{exc.args[0]}}}"}
            index, node = self._find(resolved, snapshot)
            if index is not None:
                self._mark(skill_id, str(step["id"]), index, True)
                return {"ok": True, "selector": index, "node": node, "snapshot": snapshot}
            if time.monotonic() >= deadline:
                for failed_index, _selector in ordered:
                    self._mark(skill_id, str(step["id"]), failed_index, False)
                return {"ok": False, "code": "ui_not_found",
                        "error": f"элемент не найден за {int(timeout)}с (селекторов: {len(ordered)})"}
            time.sleep(self.poll_interval)

    def _run_step(self, skill: dict, step: dict, params: dict) -> dict:
        skill_id, step_id, verb = skill["id"], str(step["id"]), step["do"]
        timeout = min(60.0, float(step.get("timeout") or 5))
        try:
            interpolated = _interpolate(step, params)
        except KeyError as exc:
            return {"ok": False, "code": "missing_param", "error": f"нет параметра ${{{exc.args[0]}}}"}
        step = interpolated
        gateway = self.gateway

        if verb == "wait":
            time.sleep(min(30.0, float(step.get("seconds") or 1)))
            return {"ok": True}

        if verb == "app.open":
            reference = str(step.get("package") or step.get("profile") or "").strip()
            if not reference:
                return {"ok": False, "code": "invalid_skill", "error": "шаг app.open: нет package/profile"}
            result = gateway.open_profile(reference, confirm=True)
            if result.get("status") == "ok":
                return {"ok": True}
            return {"ok": False, "code": "app_open_failed",
                    "error": str(result.get("error") or result.get("message") or "")[:200]}

        if verb == "ui.key":
            keycode = str(step.get("keycode") or "KEYCODE_BACK")
            if not keycode.startswith("KEYCODE_"):
                return {"ok": False, "code": "invalid_skill", "error": "keycode должен начинаться с KEYCODE_"}
            result = gateway.key(keycode, confirm=True)
            return {"ok": result.get("status") == "ok",
                    "code": "input_failed", "error": str(result.get("error") or "")[:200]}

        if verb == "ui.type":
            text = str(step.get("text") or "")[:_MAX_TEXT]
            if not text:
                return {"ok": False, "code": "invalid_skill", "error": "ui.type: пустой text"}
            clip = gateway.set_clipboard(text, confirm=True)
            if clip.get("status") != "ok":
                return {"ok": False, "code": "clipboard_failed",
                        "error": str(clip.get("error") or "")[:200]}
            time.sleep(0.3)
            result = gateway.key("KEYCODE_PASTE", confirm=True)
            return {"ok": result.get("status") == "ok",
                    "code": "input_failed", "error": str(result.get("error") or "")[:200]}

        if verb in ("ui.wait", "ui.tap"):
            found = self._wait_match(skill_id, step, params, timeout)
            if (not found["ok"] and verb == "ui.tap" and found.get("code") == "ui_not_found"
                    and step.get("heal") and self.vision is not None):
                healed = self._heal_and_tap(skill, step)
                if healed["ok"]:
                    return healed
                return {"ok": False, "code": "ui_not_found",
                        "error": f"{found.get('error')}; vision: {healed.get('error')}"[:250]}
            if not found["ok"] or verb == "ui.wait":
                if found["ok"]:
                    found.pop("node", None)
                    found.pop("snapshot", None)
                return found
            center = _node_center(found["node"])
            if center is None:
                return {"ok": False, "code": "no_bounds", "error": "у элемента нет bounds"}
            tapped = gateway.tap(center[0], center[1], confirm=True)
            if tapped.get("status") != "ok":
                return {"ok": False, "code": "tap_failed",
                        "error": str(tapped.get("error") or "")[:200]}
            return {"ok": True, "selector": found["selector"]}

        if verb == "verify":
            if step.get("foreground"):
                snapshot = self._snapshot()
                foreground = str(snapshot.get("package") or snapshot.get("package_name") or "")
                if foreground == str(step["foreground"]):
                    return {"ok": True}
                return {"ok": False, "code": "verify_failed",
                        "error": "ожидался другой foreground-пакет"}
            found = self._wait_match(skill_id, step, params, min(60.0, float(step.get("timeout") or 0)))
            if found["ok"]:
                found.pop("node", None)
                found.pop("snapshot", None)
                return found
            return found

        return {"ok": False, "code": "invalid_skill", "error": f"неизвестный глагол {verb}"}

    def _heal_and_tap(self, skill: dict, step: dict) -> dict:
        """Восстановление: скриншот → VLM ищет элемент по heal_hint → тап → обучение."""
        hint = str(step.get("heal_hint") or "").strip()
        if not hint:
            return {"ok": False, "error": "шаг без heal_hint"}
        try:
            shot = self.gateway.screenshot()
        except Exception as exc:
            return {"ok": False, "error": f"screenshot: {exc}"[:160]}
        if shot.get("status") != "ok":
            return {"ok": False, "error": f"screenshot: {shot.get('error', 'failed')}"[:160]}
        located = self.vision.locate(shot.get("file"), hint)
        if located.get("status") != "ok":
            return {"ok": False, "error": str(located.get("error") or "элемент не найден")[:160]}
        tapped = self.gateway.tap(int(located["x"]), int(located["y"]), confirm=True)
        if tapped.get("status") != "ok":
            return {"ok": False, "error": "тап по VLM-координатам не прошёл"}
        self._learn(skill["id"], str(step["id"]), int(located["x"]), int(located["y"]))
        self._event("skill_heal", {"skill": skill["id"], "step": str(step["id"]),
                                   "provider": str(located.get("provider") or "")})
        return {"ok": True, "selector": -1, "healed": True}

    # ---------------------------------------------------------------- run

    def run(self, skill_id: str, params: dict | None = None) -> dict:
        """Выполняет skill целиком; итог — данные шагов без содержимого экрана."""
        skill = self.get(skill_id)
        if skill is None:
            return {"status": "error", "code": "unknown_skill", "error": f"skill '{skill_id}' не найден"}
        params = params if isinstance(params, dict) else {}
        started = time.monotonic()
        steps_out: list[dict] = []
        for step in skill["steps"]:
            result = self._run_step(skill, step, params)
            record = {"id": str(step["id"]), "ok": bool(result.get("ok"))}
            if result.get("selector") is not None:
                record["selector"] = result["selector"]
            if result.get("healed"):
                record["healed"] = True
            if not result.get("ok"):
                if step.get("optional"):
                    record["skipped"] = True
                    steps_out.append(record)
                    continue
                steps_out.append(record)
                outcome = {"status": "error", "code": str(result.get("code") or "step_failed"),
                           "step": str(step["id"]), "error": str(result.get("error") or "")[:200],
                           "steps_done": steps_out,
                           "duration_seconds": round(time.monotonic() - started, 2)}
                self._event("skill_run", {"skill": skill_id, "ok": False,
                                          "step": str(step["id"]), "code": outcome["code"]})
                return outcome
            steps_out.append(record)
        outcome = {"status": "ok", "skill": skill_id, "steps": steps_out,
                   "duration_seconds": round(time.monotonic() - started, 2)}
        self._event("skill_run", {"skill": skill_id, "ok": True,
                                  "steps": len(steps_out), "duration": outcome["duration_seconds"]})
        return outcome
