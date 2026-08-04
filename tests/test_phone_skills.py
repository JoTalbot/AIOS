"""Тесты skill-движка Phone Brain (этап 2): загрузка, выполнение, статистика."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_core.phone_brain.handlers import Executor, JobContext, skill_handlers
from aios_core.phone_brain.skills import SkillEngine


class FakeGateway:
    """Двойник AndroidGateway с программируемыми UI-снимками."""

    def __init__(self, snapshots: list[dict]):
        self._snapshots = list(snapshots)
        self.taps: list[tuple[int, int]] = []
        self.clipboard: list[str] = []
        self.opened: list[str] = []
        self.keys: list[str] = []
        self.snapshot_calls = 0

    def ui_snapshot(self, confirm: bool = False, include_text: bool = False) -> dict:
        self.snapshot_calls += 1
        if len(self._snapshots) > 1:
            return self._snapshots.pop(0)
        return self._snapshots[0]

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
    return tmp_path


OPEN_CHAT_SKILL = {
    "id": "wa_open", "title": "WA open", "app": "whatsapp", "confirm": True,
    "steps": [
        {"id": "open", "do": "app.open", "package": "com.whatsapp"},
        {"id": "find", "do": "ui.tap", "timeout": 0,
         "selectors": [{"text": "Нет такого"}, {"resource": "com.whatsapp:id/search"}]},
        {"id": "type", "do": "ui.type", "text": "${contact}"},
    ],
}


def test_load_and_list(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    bad = root / "skills" / "phone" / "broken.json"
    bad.write_text('{"id": "broken", "steps": [{"do": "fly"}]}', "utf-8")
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "nodes": []}]))
    skills = engine.list()
    assert any(item["id"] == "wa_open" and item["steps"] == 3 for item in skills)
    assert any(item.get("error") for item in skills)  # битый файл виден в списке


def test_run_fallback_selector_and_stats(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    snapshot = {"status": "ok", "package": "com.whatsapp",
                "nodes": [_node(resource="com.whatsapp:id/search", bounds=(100, 100, 200, 140))]}
    gateway = FakeGateway([snapshot])
    engine = SkillEngine(root, gateway=gateway, poll_interval=0.01)

    result = engine.run("wa_open", params={"contact": "Мама"})
    assert result["status"] == "ok"
    assert gateway.opened == ["com.whatsapp"]
    assert gateway.taps == [(150, 120)]  # центр bounds
    assert gateway.clipboard == ["Мама"]
    assert gateway.keys == ["KEYCODE_PASTE"]
    # статистика запомнила сработавший селектор (индекс 1, первый в цепочке не совпал)
    stats = json.loads((root / "data" / "android_gateway" / "skill_stats.json").read_text("utf-8"))
    assert stats["wa_open:find"]["last_good"] == 1
    assert stats["wa_open:find"]["fail"] == {}  # первый селектор не «фейлил» — просто не совпал


def test_step_failure_marks_all_selectors(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    gateway = FakeGateway([{"status": "ok", "nodes": [_node(text="статус бар")]}])
    engine = SkillEngine(root, gateway=gateway, poll_interval=0.01)
    result = engine.run("wa_open", params={"contact": "Мама"})
    assert result["status"] == "error" and result["step"] == "find"
    stats = json.loads((root / "data" / "android_gateway" / "skill_stats.json").read_text("utf-8"))
    assert stats["wa_open:find"]["fail"] == {"0": 1, "1": 1}


def test_missing_param(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    gateway = FakeGateway([{"status": "ok", "nodes": [_node(resource="com.whatsapp:id/search")]}])
    engine = SkillEngine(root, gateway=gateway)
    result = engine.run("wa_open")  # без contact
    assert result["status"] == "error" and result["code"] == "missing_param"


def test_optional_step_skips_failure(root: Path) -> None:
    skill = {"id": "opt", "steps": [
        {"id": "maybe", "do": "ui.wait", "timeout": 0, "optional": True,
         "selectors": [{"text": "Невозможный текст"}]},
        {"id": "key", "do": "ui.key", "keycode": "KEYCODE_HOME"}]}
    _write_skill(root, skill)
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "nodes": []}]), poll_interval=0.01)
    result = engine.run("opt")
    assert result["status"] == "ok"
    assert result["steps"][0]["skipped"] and result["steps"][1]["ok"]


def test_verify_foreground(root: Path) -> None:
    skill = {"id": "ver", "steps": [
        {"do": "verify", "foreground": "com.whatsapp"}]}
    _write_skill(root, skill)
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "package": "com.whatsapp", "nodes": []}]))
    assert engine.run("ver")["status"] == "ok"
    engine2 = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "package": "com.other", "nodes": []}]))
    failed = engine2.run("ver")
    assert failed["status"] == "error" and failed["code"] == "verify_failed"


def test_unknown_skill(root: Path) -> None:
    engine = SkillEngine(root, gateway=FakeGateway([]))
    assert engine.run("ghost")["code"] == "unknown_skill"


def test_ui_unavailable(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "offline"}]))
    result = engine.run("wa_open", params={"contact": "Мама"})
    assert result["code"] == "ui_unavailable"


# ----------------------------------------------------------- интеграция с очередью

def _ctx() -> JobContext:
    supervisor = SimpleNamespace(is_online=lambda: True, companion_ready=lambda: True)
    return JobContext(root=Path("/tmp"), gateway=None, supervisor=supervisor, events=None)


def test_skill_run_confirm_gate(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)  # confirm: true
    engine = SkillEngine(root, gateway=FakeGateway([]))
    executor = Executor(_ctx(), handlers=skill_handlers(engine))
    verdict, payload = executor.execute({"id": 1, "kind": "skill.run",
                                         "payload": {"skill": "wa_open"}})
    assert verdict == "need_confirm" and payload["action"] == "phone_skill:wa_open"


def test_skill_run_no_confirm_needed_for_open_skill(root: Path) -> None:
    skill = {"id": "free", "confirm": False,
             "steps": [{"do": "ui.key", "keycode": "KEYCODE_HOME"}]}
    _write_skill(root, skill)
    engine = SkillEngine(root, gateway=FakeGateway([{"status": "ok", "nodes": []}]))
    executor = Executor(_ctx(), handlers=skill_handlers(engine))
    verdict, _ = executor.execute({"id": 1, "kind": "skill.run", "payload": {"skill": "free"}})
    assert verdict == "done"


def test_skill_run_unknown_not_retried(root: Path) -> None:
    engine = SkillEngine(root, gateway=FakeGateway([]))
    executor = Executor(_ctx(), handlers=skill_handlers(engine))
    verdict, payload = executor.execute({"id": 1, "kind": "skill.run",
                                         "payload": {"skill": "ghost", "confirm": True}})
    assert verdict == "fail" and payload["retry"] is False


def test_skill_list_handler(root: Path) -> None:
    _write_skill(root, OPEN_CHAT_SKILL)
    engine = SkillEngine(root, gateway=FakeGateway([]))
    executor = Executor(_ctx(), handlers=skill_handlers(engine))
    verdict, payload = executor.execute({"id": 1, "kind": "skill.list", "payload": {}})
    assert verdict == "done"
    assert any(s["id"] == "wa_open" for s in payload["skills"])
