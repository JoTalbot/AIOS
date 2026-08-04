"""Executor Phone Brain: реестр типов задач, гейты, таймауты.

Контракт обработчика: fn(payload, ctx) -> dict со "status":
    "ok"       → задача выполнена (done)
    "error"    → провал (fail; повтор, если не "retry": false)
    "offline"  → устройство недоступно (defer без сжигания попытки)

Гейты (middleware безопасности прежнего шлюза, перенесён в единую точку):
* confirm_action — требуется payload["confirm"]=true, иначе need_confirm;
* needs_device    — устройство должно быть online, иначе defer;
* needs_companion — Companion должен быть жив, иначе defer;
* precheck        — кастомная проверка payload (например, include_text ⇒ confirm).
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from aios_core.android_gateway import AndroidGateway

Verdict = tuple[str, dict]  # ("done"|"fail"|"defer"|"need_confirm", payload)


@dataclass
class JobContext:
    """Контекст исполнения, собирается демоном один раз."""
    root: Path
    gateway: AndroidGateway
    supervisor: Any
    events: Any
    store: Any = None


@dataclass
class Handler:
    kind: str
    fn: Callable[[dict, JobContext], dict]
    timeout: int = 120
    needs_device: bool = True
    needs_companion: bool = False
    confirm_action: str | None = None
    precheck: Callable[[dict], dict | None] | None = None
    description: str = ""

    def meta(self) -> dict:
        return {"kind": self.kind, "timeout": self.timeout, "needs_device": self.needs_device,
                "needs_companion": self.needs_companion,
                "confirm_action": self.confirm_action or "", "description": self.description}


class Executor:
    """Исполняет задачи последовательно (экран устройства — общий ресурс)."""

    def __init__(self, ctx: JobContext, handlers: list[Handler] | None = None):
        self.ctx = ctx
        self._handlers: dict[str, Handler] = {}
        for handler in handlers or BUILTIN_HANDLERS:
            self.register(handler)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phone-brain-job")

    def register(self, handler: Handler) -> None:
        self._handlers[handler.kind] = handler

    def kinds(self) -> list[str]:
        return sorted(self._handlers)

    def handlers_meta(self) -> list[dict]:
        return [self._handlers[kind].meta() for kind in self.kinds()]

    def execute(self, job: dict) -> Verdict:
        kind = str(job.get("kind") or "")
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        handler = self._handlers.get(kind)
        if handler is None:
            return ("fail", {"status": "error", "error": f"Неизвестный тип задачи: {kind}",
                             "retry": False})
        if handler.confirm_action and not payload.get("confirm"):
            return ("need_confirm", {"status": "need_confirm", "action": handler.confirm_action,
                                     "kind": kind})
        if handler.precheck is not None:
            failed_check = handler.precheck(payload)
            if failed_check is not None:
                return ("need_confirm", failed_check)
        if handler.needs_device and not self._device_online():
            return ("defer", {"reason": "device_offline"})
        if handler.needs_companion and not self._companion_ready():
            return ("defer", {"reason": "companion_offline"})
        future = self._pool.submit(handler.fn, payload, self.ctx)
        try:
            result = future.result(timeout=handler.timeout)
        except FutureTimeout:
            return ("fail", {"status": "error", "error": f"Таймаут обработчика ({handler.timeout}с)"})
        except Exception as exc:  # noqa: BLE001 — обработчик не должен ронять воркер
            return ("fail", {"status": "error", "error": str(exc)[:300]})
        if not isinstance(result, dict):
            return ("fail", {"status": "error", "error": "Обработчик вернул не-JSON результат"})
        status = str(result.get("status") or "")
        if status == "ok":
            return ("done", result)
        if status == "offline":
            return ("defer", {"reason": "device_offline"})
        if status == "need_confirm":
            return ("need_confirm", result)
        return ("fail", {"status": "error",
                         "error": str(result.get("error") or result.get("message") or status or "unknown")[:300],
                         "retry": bool(result.get("retry", True))})

    def _device_online(self) -> bool:
        try:
            return bool(self.ctx.supervisor.is_online())
        except Exception:
            return False

    def _companion_ready(self) -> bool:
        try:
            return bool(self.ctx.supervisor.companion_ready())
        except Exception:
            return False


# ------------------------------------------------------------------ handlers

def _h_device_connect(payload: dict, ctx: JobContext) -> dict:
    """Принудительный reconnect ADB с проверкой результата."""
    try:
        connect_result = ctx.gateway.connect()
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
    try:
        probe = ctx.gateway.status()
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
    if probe.get("connected"):
        return {"status": "ok", "connect": connect_result, "device": probe}
    return {"status": "error", "error": str(connect_result.get("message") or "Нет соединения")[:200],
            "connect": connect_result}


def _h_device_status(payload: dict, ctx: JobContext) -> dict:
    return {"status": "ok", "device": ctx.gateway.status()}


def _h_screenshot(payload: dict, ctx: JobContext) -> dict:
    return ctx.gateway.screenshot()


def _precheck_snapshot(payload: dict) -> dict | None:
    if payload.get("include_text") and not payload.get("confirm"):
        return {"status": "need_confirm", "action": "android_ui_text"}
    return None


def _h_ui_snapshot(payload: dict, ctx: JobContext) -> dict:
    result = ctx.gateway.ui_snapshot(confirm=True, include_text=bool(payload.get("include_text")))
    if result.get("status") == "unconfigured":
        return {"status": "error", "error": result.get("error", "Companion не настроен"), "retry": False}
    return result


def _h_app_open(payload: dict, ctx: JobContext) -> dict:
    reference = str(payload.get("package") or payload.get("profile") or "").strip()
    if not reference:
        return {"status": "error", "error": "Нужен package или profile", "retry": False}
    result = ctx.gateway.open_profile(reference, confirm=True)
    if result.get("status") == "ok":
        return {"status": "ok", **{k: v for k, v in result.items() if k != "status"}}
    return {"status": "error", "error": str(result.get("error") or result.get("message") or "")[:200]}


def _run_json_script(path: Path, timeout: int) -> dict:
    """Запускает repo-скрипт и разбирает JSON из stdout (последний JSON-документ)."""
    proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=timeout)
    output = (proc.stdout or "").strip()
    parsed: dict = {}
    if output:
        try:
            value = json.loads(output)
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            for line in reversed(output.splitlines()):
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    parsed = value
                    break
    return {"exit_code": proc.returncode, "output": parsed,
            "stdout_tail": output[-300:], "stderr_tail": (proc.stderr or "")[-300:]}


def _h_notify_collect(payload: dict, ctx: JobContext) -> dict:
    """Сбор уведомлений выбранных приложений в общий инбокс (обёртка над коллектором)."""
    ran = _run_json_script(ctx.root / "run_android_notification_collector.py", timeout=100)
    if ran["exit_code"] == 0:
        return {"status": "ok", "collector": ran["output"]}
    return {"status": "error",
            "error": (ran["stderr_tail"] or ran["stdout_tail"] or f"exit {ran['exit_code']}")[:200]}


def _h_device_location(payload: dict, ctx: JobContext) -> dict:
    """Текущая геолокация через Companion (бот подтверждает на своей стороне)."""
    return ctx.gateway.location(confirm=True)


def _h_device_pull(payload: dict, ctx: JobContext) -> dict:
    """Забрать файл из разрешённых папок общего хранилища телефона."""
    path = str(payload.get("path") or "").strip()
    if not path:
        return {"status": "error", "error": "Нужен path файла", "retry": False}
    return ctx.gateway.pull_file(path, confirm=True)


def _h_queue_confirm(payload: dict, ctx: JobContext) -> dict:
    """Одобрение черновика владельцем: need_confirm → обратно в очередь с confirm."""
    if ctx.store is None:
        return {"status": "error", "error": "store недоступен", "retry": False}
    try:
        job_id = int(payload.get("id") or 0)
    except (TypeError, ValueError):
        job_id = 0
    if not job_id:
        return {"status": "error", "error": "Нужен id задачи", "retry": False}
    result = ctx.store.confirm_job(job_id)
    if result.get("status") == "error":
        result["retry"] = False
    return result


# Read-only команды legacy CLI, доступные через очередь (мост для миграции бота).
_READ_COMMANDS = {
    "status", "apps", "profiles", "companion", "notifications", "accessibility",
    "capture-status", "location-status", "files", "screenshot", "ui-dump", "audit",
}


def _h_gateway_cli(payload: dict, ctx: JobContext) -> dict:
    """Безопасный passthrough read-only команд run_android_gateway.py.

    Позволяет переводить вызовы бота на очередь без изменения семантики
    подтверждений: сюда просто не включены команды, меняющие UI.
    """
    command = str(payload.get("command") or "status").strip()
    if command not in _READ_COMMANDS:
        return {"status": "error", "retry": False,
                "error": f"Команда '{command}' не входит в read-only whitelist"}
    cmd = [sys.executable, str(ctx.root / "run_android_gateway.py"), command]
    args = payload.get("args")
    if isinstance(args, list):
        cmd += [str(a) for a in args[:3]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    output = (proc.stdout or "").strip()
    try:
        parsed = json.loads(output) if output else {}
    except json.JSONDecodeError:
        parsed = {"raw": output[-400:]}
    if proc.returncode in (0, 1) and isinstance(parsed, dict) and parsed.get("status") in (
            "ok", "offline", "unregistered"):
        return {"status": "ok", "command": command, "output": parsed}
    return {"status": "error",
            "error": str((proc.stderr or "")[-200:] or parsed.get("error") or f"exit {proc.returncode}")[:200],
            "command": command, "output": parsed if isinstance(parsed, dict) else {}}


BUILTIN_HANDLERS: list[Handler] = [
    Handler("device.connect", _h_device_connect, timeout=90, needs_device=False,
            description="Переподключить ADB к телефону и проверить соединение"),
    Handler("device.status", _h_device_status, timeout=45, needs_device=False,
            description="Текущее состояние устройства и Companion"),
    Handler("gateway.cli", _h_gateway_cli, timeout=100, needs_device=False,
            description="Read-only команды шлюза (status/apps/profiles/notifications/ui-dump/...)"),
    Handler("ui.screenshot", _h_screenshot, timeout=90,
            description="Скриншот экрана в data/android_gateway/screenshots/"),
    Handler("ui.snapshot", _h_ui_snapshot, timeout=60, needs_companion=True,
            precheck=_precheck_snapshot,
            description="Снимок UI-дерева; include_text требует confirm=true"),
    Handler("app.open", _h_app_open, timeout=75, confirm_action="android_app_open",
            description="Открыть приложение по профилю/pакету (нужен confirm=true)"),
    Handler("notify.collect", _h_notify_collect, timeout=120, needs_companion=True,
            description="Сбор уведомлений приложений в инбокс AIOS"),
    Handler("device.location", _h_device_location, timeout=45, needs_companion=True,
            confirm_action="android_location",
            description="Текущая геолокация телефона (нужен confirm=true)"),
    Handler("device.pull", _h_device_pull, timeout=150,
            confirm_action="android_pull_file",
            description="Забрать файл из разрешённых папок телефона (confirm=true)"),
    Handler("queue.confirm", _h_queue_confirm, timeout=15, needs_device=False,
            description="Подтвердить черновик-задачу (need_confirm → выполнение)"),
]


# ------------------------------------------------------- skill engine (этап 2)

def skill_handlers(engine: Any) -> list[Handler]:
    """Фабрика обработчиков skill-движка: выполнение и список декларативных skills."""

    def _run(payload: dict, ctx: JobContext) -> dict:
        skill_id = str(payload.get("skill") or "").strip()
        if not skill_id:
            return {"status": "error", "error": "Нужен skill id", "retry": False}
        result = engine.run(skill_id, params=payload.get("params") or {})
        if result.get("status") == "ok":
            return result
        code = str(result.get("code") or "")
        # Неизвестный/битый skill и нехватка параметров повторять бессмысленно.
        retry = code not in ("unknown_skill", "missing_param", "invalid_skill")
        step_info = f"шаг {result.get('step')}: " if result.get("step") else ""
        return {"status": "error", "retry": retry, "engine": result,
                "error": (step_info + str(result.get("error") or code))[:250]}

    def _precheck(payload: dict) -> dict | None:
        skill = engine.get(str(payload.get("skill") or ""))
        if skill and skill.get("confirm") and not payload.get("confirm"):
            return {"status": "need_confirm", "action": f"phone_skill:{skill['id']}"}
        return None

    def _list(payload: dict, ctx: JobContext) -> dict:
        engine.reload()  # подхватываем новые/изменённые файлы без рестарта демона
        return {"status": "ok", "skills": engine.list()}

    return [
        Handler("skill.run", _run, timeout=280, needs_companion=True, precheck=_precheck,
                description="Выполнить декларативный skill из skills/phone/ (список — skill.list)"),
        Handler("skill.list", _list, timeout=15, needs_device=False,
                description="Список доступных phone-skills и ошибки загрузки"),
    ]


# ------------------------------------------------- planner + vision (этап 3)

def planner_handlers(planner: Any, vision: Any) -> list[Handler]:
    """Фабрика обработчиков LLM-планировщика и VLM-тапа."""

    def _plan_run(payload: dict, ctx: JobContext) -> dict:
        goal = str(payload.get("goal") or "").strip()
        if not goal:
            return {"status": "error", "error": "Пустая цель", "retry": False}
        result = planner.run(goal)
        if result.get("status") == "ok":
            return result
        code = str(result.get("code") or "")
        # Ошибки синтеза плана повторять бессмысленно; ошибки провайдера и UI — да.
        retry = code in ("llm_unavailable", "ui_unavailable", "ui_not_found",
                         "app_open_failed", "tap_failed")
        return {"status": "error", "retry": retry,
                "error": str(result.get("error") or code)[:250],
                "plan": result.get("plan") or [], "executed": result.get("executed") or []}

    def _vision_tap(payload: dict, ctx: JobContext) -> dict:
        hint = str(payload.get("hint") or "").strip()
        if not hint:
            return {"status": "error", "error": "Нужен hint (описание элемента)", "retry": False}
        shot = ctx.gateway.screenshot()
        if shot.get("status") != "ok":
            status = "offline" if shot.get("status") == "offline" else "error"
            return {"status": status, "error": str(shot.get("error") or "screenshot failed")[:160]}
        located = vision.locate(shot.get("file"), hint)
        if located.get("status") != "ok":
            return {"status": "error", "error": str(located.get("error"))[:180]}
        tapped = ctx.gateway.tap(int(located["x"]), int(located["y"]), confirm=True)
        if tapped.get("status") != "ok":
            return {"status": "error", "error": "тап по VLM-координатам не прошёл"}
        return {"status": "ok", "x": located["x"], "y": located["y"],
                "provider": located.get("provider")}

    return [
        Handler("plan.run", _plan_run, timeout=280, needs_companion=True,
                confirm_action="phone_plan_run",
                description="Цель на русском → LLM-план из skills → выполнение (confirm=true)"),
        Handler("vision.tap", _vision_tap, timeout=120, needs_companion=True,
                confirm_action="phone_vision_tap",
                description="Тап по элементу, найденному VLM по описанию hint (confirm=true)"),
    ]


# ------------------------------------------------- reaction engine (этап 4)

def reaction_handlers(reactor: Any) -> list[Handler]:
    """Фабрика обработчиков reaction engine: ручной цикл и список правил."""

    def _tick(payload: dict, ctx: JobContext) -> dict:
        result = reactor.tick()
        if result.get("status") == "ok":
            return result
        if result.get("status") in ("offline", "unconfigured", "unregistered"):
            return {"status": "offline", "error": result.get("error", "")}
        return {"status": "error", "error": str(result.get("error") or "")[:200]}

    def _rules(payload: dict, ctx: JobContext) -> dict:
        reactor.reload()
        return {"status": "ok", "rules": reactor.list_rules(), "state": reactor.state_summary()}

    return [
        Handler("react.tick", _tick, timeout=90, needs_device=False,
                description="Один цикл оценки уведомлений по правилам phone_reactions/"),
        Handler("react.rules", _rules, timeout=15, needs_device=False,
                description="Список правил реакций и состояние дедупликации"),
    ]
