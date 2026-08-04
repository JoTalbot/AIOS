"""Тесты этапа 3: LLM-планировщик, VLM-локатор, самовосстановление селекторов."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_core.phone_brain.handlers import Executor, JobContext, planner_handlers
from aios_core.phone_brain.planner import PhonePlanner
from aios_core.phone_brain.skills import SkillEngine
from aios_core.phone_brain.vision import VisionLocator, _extract_json


class FakeGateway:
    def __init__(self, snapshots: list[dict]):
        self._snapshots = list(snapshots)
        self.taps: list[tuple[int, int]] = []
        self.clipboard: list[str] = []
        self.opened: list[str] = []
        self.keys: list[str] = []
        self.shots = 0

    def ui_snapshot(self, confirm: bool = False, include_text: bool = False) -> dict:
        if len(self._snapshots) > 1:
            return self._snapshots.pop(0)
        return self._snapshots[0]

    def screenshot(self) -> dict:
        self.shots += 1
        return {"status": "ok", "file": str(self._shot_path)}

    _shot_path = Path("/tmp/fake_shot.png")

    def open_profile(self, reference: str, confirm: bool = False) -> dict:
        self.opened.append(reference)
        return {"status": "ok"}

    def tap(self, x: int, y: int, confirm: bool = False) -> dict:
        self.taps.append((x, y))
        return {"status": "ok"}

    def set_clipboard(self, text: str, confirm: bool = False) -> dict:
        self.clipboard.append(text)
        return {"status": "ok"}

    def key(self, keycode: str, confirm: bool = False) -> dict:
        self.keys.append(keycode)
        return {"status": "ok"}


def _node(text: str = "", desc: str = "", resource: str = "",
          bounds: tuple[int, int, int, int] = (0, 0, 100, 40)) -> dict:
    return {"text": text, "description": desc, "resource": resource, "bounds": list(bounds)}


def _write_skill(root: Path, data: dict) -> None:
    skills_dir = root / "skills" / "phone"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / f"{data['id']}.json").write_text(json.dumps(data, ensure_ascii=False), "utf-8")


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / "data" / "android_gateway").mkdir(parents=True)
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG fake")
    FakeGateway._shot_path = shot
    return tmp_path


SKILL = {
    "id": "wa_send", "title": "WA send", "app": "whatsapp", "confirm": True,
    "params": ["contact", "text"],
    "steps": [
        {"id": "open", "do": "app.open", "package": "com.whatsapp"},
        {"id": "find", "do": "ui.tap", "timeout": 0,
         "selectors": [{"resource": "com.whatsapp:id/search"}]},
        {"id": "type", "do": "ui.type", "text": "${text}"},
    ],
}


def _engine(root: Path, gateway: FakeGateway, vision: object = None) -> SkillEngine:
    _write_skill(root, SKILL)
    return SkillEngine(root, gateway=gateway, vision=vision, poll_interval=0.01)


# ------------------------------------------------------------------ planner

def test_plan_valid(root: Path) -> None:
    engine = _engine(root, FakeGateway([{"status": "ok", "nodes": []}]))
    chat = lambda messages, **kw: '{"plan": [{"skill": "wa_send", "params": {"contact": "Мама", "text": "ок"}}]}'
    planner = PhonePlanner(engine, chat=chat)
    planned = planner.plan("напиши маме что я ок")
    assert planned["status"] == "ok"
    assert planned["plan"][0]["params"] == {"contact": "Мама", "text": "ок"}


def test_plan_missing_param_rejected(root: Path) -> None:
    engine = _engine(root, FakeGateway([{"status": "ok", "nodes": []}]))
    chat = lambda messages, **kw: '{"plan": [{"skill": "wa_send", "params": {"contact": "Мама"}}]}'
    result = PhonePlanner(engine, chat=chat).plan("что-то")
    assert result["code"] == "missing_param"


def test_plan_unknown_skill_rejected(root: Path) -> None:
    engine = _engine(root, FakeGateway([{"status": "ok", "nodes": []}]))
    chat = lambda messages, **kw: '{"plan": [{"skill": "ghost", "params": {}}]}'
    result = PhonePlanner(engine, chat=chat).plan("что-то")
    assert result["code"] == "unknown_skill"


def test_plan_repair_attempt_on_bad_json(root: Path) -> None:
    engine = _engine(root, FakeGateway([{"status": "ok", "nodes": []}]))
    calls = {"n": 0}

    def chat(messages: list, **kw) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "```json\nbroken"
        return '{"plan": [{"skill": "wa_send", "params": {"contact": "Мама", "text": "скоро"}}]}'

    planned = PhonePlanner(engine, chat=chat).plan("напиши")
    assert planned["status"] == "ok" and calls["n"] == 2


def test_planner_refusal(root: Path) -> None:
    engine = _engine(root, FakeGateway([{"status": "ok", "nodes": []}]))
    chat = lambda messages, **kw: '{"error": "нет подходящего сценария"}'
    result = PhonePlanner(engine, chat=chat).plan("почини телевизор")
    assert result["code"] == "planner_refused"


def test_planner_run_executes_and_stops_on_failure(root: Path) -> None:
    gateway = FakeGateway([{"status": "ok", "nodes": []}])  # узлов нет → шаг find упадёт
    engine = _engine(root, gateway)
    chat = lambda messages, **kw: ('{"plan": [{"skill": "wa_send", "params": {"contact": "Мама", "text": "ок"}},'
                                   ' {"skill": "wa_send", "params": {"contact": "Папа", "text": "ок"}}]}')
    result = PhonePlanner(engine, chat=chat).run("напиши маме и папе")
    assert result["status"] == "error"
    assert len(result["executed"]) == 1  # цепочка остановилась на первом провале


def test_planner_run_ok(root: Path) -> None:
    snapshot = {"status": "ok", "nodes": [_node(resource="com.whatsapp:id/search")]}
    engine = _engine(root, FakeGateway([snapshot]))
    chat = lambda messages, **kw: '{"plan": [{"skill": "wa_send", "params": {"contact": "Мама", "text": "ок"}}]}'
    result = PhonePlanner(engine, chat=chat).run("напиши маме")
    assert result["status"] == "ok" and result["executed"][0]["ok"]


# ------------------------------------------------------------------ vision

def test_extract_json() -> None:
    assert _extract_json('бла {"found": true, "x": 10, "y": 20} бла') == {"found": True, "x": 10, "y": 20}
    assert _extract_json("нет json") is None
    assert _extract_json('{"a": {"b": 1}}') == {"a": {"b": 1}}


def test_vision_locate(root: Path) -> None:
    def ask(key: str, b64: str, hint: str) -> dict:
        assert b64  # картинка дошла в base64
        return {"found": True, "x": 120, "y": 340}

    locator = VisionLocator(providers=[("fake", ask, "k")])
    result = locator.locate(root / "shot.png", "кнопка поиска")
    assert result == {"status": "ok", "x": 120, "y": 340, "provider": "fake"}


def test_vision_not_found_and_out_of_bounds(root: Path) -> None:
    locator = VisionLocator(providers=[("fake", lambda k, b, h: {"found": False}, "k")])
    assert locator.locate(root / "shot.png", "x")["status"] == "error"
    wild = VisionLocator(providers=[("fake", lambda k, b, h: {"found": True, "x": 99999, "y": 1}, "k")])
    assert "недоступны" in wild.locate(root / "shot.png", "x")["error"]


# ------------------------------------------------------------- self-healing

def test_heal_and_learn_then_reuse(root: Path) -> None:
    """Селекторы падают → VLM находит элемент → точка запоминается и
    используется при следующем запуске БЕЗ нового VLM-вызова."""
    heal_skill = {
        "id": "healed", "confirm": True, "steps": [
            {"id": "find", "do": "ui.tap", "timeout": 0, "heal": True,
             "heal_hint": "search button",
             "selectors": [{"resource": "old.id/dead_selector"}]},
        ],
    }
    _write_skill(root, heal_skill)
    empty_snapshot = {"status": "ok", "nodes": [_node(text="шапка", bounds=(0, 0, 50, 20))]}
    gateway = FakeGateway([empty_snapshot])

    class FakeVision:
        calls = 0

        def locate(self, image: str, hint: str) -> dict:
            self.calls += 1
            assert hint == "search button"
            return {"status": "ok", "x": 540, "y": 200, "provider": "fake"}

    vision = FakeVision()
    engine = SkillEngine(root, gateway=gateway, vision=vision, poll_interval=0.01)

    first = engine.run("healed")
    assert first["status"] == "ok" and first["steps"][0].get("healed")
    assert gateway.taps == [(540, 200)] and vision.calls == 1

    stats = json.loads((root / "data" / "android_gateway" / "skill_stats.json").read_text("utf-8"))
    assert stats["healed:find"]["learned"]["center"] == [540, 200]

    # Второй запуск: узел появился рядом с выученной точкой → находим без VLM.
    engine2 = SkillEngine(root, gateway=FakeGateway([
        {"status": "ok", "nodes": [_node(text="Поиск", bounds=(500, 170, 580, 230))]},  # центр (540,200)
    ]), vision=vision, poll_interval=0.01)
    second = engine2.run("healed")
    assert second["status"] == "ok" and second["steps"][0]["selector"] == -1
    assert vision.calls == 1  # VLM больше не понадобился


def test_heal_disabled_without_vision(root: Path) -> None:
    heal_skill = {
        "id": "noheal", "confirm": True, "steps": [
            {"id": "find", "do": "ui.tap", "timeout": 0, "heal": True, "heal_hint": "x",
             "selectors": [{"resource": "dead"}]},
        ],
    }
    _write_skill(root, heal_skill)
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "nodes": []}]),
                         vision=None, poll_interval=0.01)
    result = engine.run("noheal")
    assert result["status"] == "error" and result["code"] == "ui_not_found"
    assert "vision" not in result["error"]  # без vision — обычная ошибка цепочки


# ------------------------------------------------------- handlers integration

def test_plan_run_confirm_gate(root: Path) -> None:
    engine = _engine(root, FakeGateway([]))
    planner = PhonePlanner(engine, chat=lambda m, **k: "{}")
    vision = VisionLocator(providers=[])
    supervisor = SimpleNamespace(is_online=lambda: True, companion_ready=lambda: True)
    ctx = JobContext(root=Path("/tmp"), gateway=None, supervisor=supervisor, events=None)
    executor = Executor(ctx, handlers=planner_handlers(planner, vision))
    verdict, payload = executor.execute({"id": 1, "kind": "plan.run",
                                         "payload": {"goal": "напиши маме"}})
    assert verdict == "need_confirm" and payload["action"] == "phone_plan_run"

    verdict2, payload2 = executor.execute({"id": 2, "kind": "vision.tap",
                                           "payload": {"hint": "кнопка"}})
    assert verdict2 == "need_confirm" and payload2["action"] == "phone_vision_tap"
