"""Подтверждаемые сценарии для приложений на реальном Android-телефоне.

Модуль намеренно не является «автокликером».  Он использует AIOS Companion
только после явной команды владельца и реализует короткие, проверяемые шаги:
открыть чат, вставить черновик, затем отдельно подтвердить отправку.  Полный
текст экрана никогда не пишется в журнал и не возвращается из технических
статусов.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .android_gateway import AndroidGateway


UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _read(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _parse_time(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _fold(value: object) -> str:
    return " ".join(str(value or "").casefold().replace("…", " ").split())


def _same_draft_text(left: object, right: object) -> bool:
    """Compare the displayed compose text without weakening its meaning.

    Accessibility may normalise line endings, but changes in case, spaces or
    characters must block sending rather than be treated as equivalent.
    """
    normalise = lambda value: str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return normalise(left) == normalise(right)


def _bounds(node: dict) -> tuple[int, int, int, int] | None:
    raw = node.get("bounds")
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        left, top, right, bottom = (int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]))
    except (TypeError, ValueError):
        return None
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _area(bounds: tuple[int, int, int, int]) -> int:
    return max(1, bounds[2] - bounds[0]) * max(1, bounds[3] - bounds[1])


def _contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _mask_sensitive(text: str) -> str:
    """Mask codes/cards even when the owner explicitly asks to read a chat."""
    masked = str(text or "")
    # Card-like sequences first so their pieces are not handled as OTPs.
    masked = re.sub(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", "[номер скрыт]", masked)
    masked = re.sub(r"(?<!\d)\d{4,8}(?!\d)", "[код скрыт]", masked)
    masked = re.sub(r"(?<!\d)(?:\+?380|0)\d[\d ()-]{7,14}(?!\d)", "[телефон скрыт]", masked)
    return masked


class WorkflowStore:
    """Private short-lived state for explicitly created drafts/routes."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "data" / "android_gateway" / "phone_workflows.json"

    def _load(self) -> dict[str, dict]:
        raw = _read(self.path, {})
        now = _now()
        active: dict[str, dict] = {}
        for workflow_id, item in raw.items() if isinstance(raw, dict) else []:
            if not isinstance(item, dict):
                continue
            expires = _parse_time(item.get("expires_at"))
            if expires and expires > now:
                active[str(workflow_id)] = item
        if active != raw:
            _write(self.path, active)
        return active

    def create(self, kind: str, package: str, data: dict, ttl_seconds: int = 300) -> dict:
        ttl = max(30, min(int(ttl_seconds), 900))
        workflows = self._load()
        workflow_id = secrets.token_urlsafe(10)
        created = _now()
        record = {
            "kind": str(kind)[:60],
            "package": str(package),
            "state": "prepared",
            "created_at": _iso(created),
            "expires_at": _iso(created + timedelta(seconds=ttl)),
            "data": data,
        }
        workflows[workflow_id] = record
        _write(self.path, workflows)
        return {"id": workflow_id, **record}

    def get(self, workflow_id: str, kind: str | None = None, package: str | None = None) -> dict | None:
        record = self._load().get(str(workflow_id))
        if not record:
            return None
        if kind and record.get("kind") != kind:
            return None
        if package and record.get("package") != package:
            return None
        return {"id": str(workflow_id), **record}

    def update(self, workflow_id: str, **changes: Any) -> dict | None:
        workflows = self._load()
        record = workflows.get(str(workflow_id))
        if not record:
            return None
        record.update(changes)
        workflows[str(workflow_id)] = record
        _write(self.path, workflows)
        return {"id": str(workflow_id), **record}


class AppCalibrationStore:
    """Persist only non-sensitive UI capability flags for an app.

    It intentionally contains no screen text, addresses, chat names, account
    data or screenshots.  The short record lets the route adapters report
    whether their known controls are still present after an app update.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "data" / "android_gateway" / "app_ui_calibrations.json"

    def get(self, profile: str) -> dict:
        value = _read(self.path, {})
        item = value.get(str(profile)) if isinstance(value, dict) else None
        return item if isinstance(item, dict) else {}

    def save(self, profile: str, package: str, *, nodes: int, editable: int, clickable: int, selectors: dict[str, bool]) -> dict:
        all_items = _read(self.path, {})
        if not isinstance(all_items, dict):
            all_items = {}
        item = {
            "package": str(package),
            "checked_at": _iso(),
            "nodes": max(0, int(nodes)),
            "editable": max(0, int(editable)),
            "clickable": max(0, int(clickable)),
            "selectors": {str(key): bool(value) for key, value in selectors.items()},
        }
        all_items[str(profile)] = item
        _write(self.path, all_items)
        return item


class ActiveAppAdapter:
    """Base class that refuses to act when another app is foregrounded."""

    package = ""
    profile = ""
    title = "Android app"

    def __init__(self, gateway: AndroidGateway):
        self.gateway = gateway
        self.store = WorkflowStore(gateway.root)
        self.calibrations = AppCalibrationStore(gateway.root)

    def _available(self) -> bool:
        profiles = self.gateway.app_profiles().get("profiles") or []
        for profile in profiles:
            if profile.get("id") == self.profile:
                return self.package in (profile.get("installed") or [])
        # A package can be used by a dedicated adapter even if a legacy profile
        # cache did not know about it yet.
        return self.package in (self.gateway.apps(limit=2000).get("apps") or [])

    def status(self) -> dict:
        available = self._available()
        access = self.gateway.accessibility()
        ui = self.gateway.ui_snapshot(confirm=True, include_text=False)
        active = bool(ui.get("status") == "ok" and ui.get("package") == self.package)
        return {
            "status": "ok" if available else "not_installed",
            "title": self.title,
            "package": self.package,
            "available": available,
            "accessibility": bool(access.get("status") == "ok" and access.get("enabled")),
            "active": active,
            # No package name, node labels or screen text is returned here.
            "ui_ready": ui.get("status") == "ok" and bool(ui.get("package")),
        }

    def _active_ui(self, include_text: bool = True) -> dict:
        return self.gateway.active_app_ui(self.package, confirm=True, include_text=include_text)

    def _wait_active_ui(self, wait_seconds: float = 2.0, include_text: bool = True) -> dict:
        """Wait briefly for a launched app without interacting with its UI."""
        deadline = time.monotonic() + max(0.2, min(float(wait_seconds), 8.0))
        last: dict = {}
        while True:
            last = self._active_ui(include_text=include_text)
            if last.get("status") == "ok" and last.get("nodes"):
                return last
            if time.monotonic() >= deadline:
                return last
            time.sleep(0.35)

    def _calibration_selectors(self, nodes: list[dict]) -> dict[str, bool]:
        return {}

    def _wait_for_calibrated_ui(self, wait_seconds: float = 3.0) -> tuple[dict, dict[str, bool]]:
        """Wait past a splash screen until known non-sensitive controls appear."""
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 15.0))
        last: dict = {}
        selectors: dict[str, bool] = {}
        while True:
            last = self._active_ui(include_text=True)
            if last.get("status") == "ok":
                selectors = self._calibration_selectors(last.get("nodes") or [])
                # Apps with no custom selectors still return after the first
                # real tree; route apps wait for a field/control or timeout.
                if not selectors or any(selectors.values()):
                    return last, selectors
            if time.monotonic() >= deadline:
                return last, selectors
            time.sleep(0.35)

    def _save_calibration(self, snapshot: dict, selectors: dict[str, bool]) -> dict:
        nodes = snapshot.get("nodes") or []
        return self.calibrations.save(
            self.profile, self.package, nodes=len(nodes),
            editable=sum(bool(node.get("editable")) for node in nodes),
            clickable=sum(bool(node.get("clickable")) for node in nodes),
            selectors=selectors,
        )

    def calibrate(self, confirm: bool = False, wait_seconds: float = 3.0) -> dict:
        """Open a chosen app and record a text-free control capability map."""
        if not confirm:
            return {"status": "need_confirm", "action": "android_calibrate_app", "package": self.package}
        opened = self.open(confirm=True)
        if opened.get("status") != "ok":
            return opened
        snapshot, selectors = self._wait_for_calibrated_ui(wait_seconds=wait_seconds)
        if snapshot.get("status") != "ok":
            return snapshot
        record = self._save_calibration(snapshot, selectors)
        return {"status": "calibrated", "title": self.title, "selectors": selectors,
                "nodes": record["nodes"], "editable": record["editable"], "clickable": record["clickable"]}

    def _tap_node(self, node: dict) -> dict:
        bounds = _bounds(node)
        if not bounds:
            return {"status": "error", "error": "Элемент интерфейса не имеет корректных координат"}
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2
        return self.gateway.tap(x, y, confirm=True)

    @staticmethod
    def _unique_editable(nodes: list[dict]) -> dict | None:
        """Return an unambiguous on-screen text input, never guessing among many."""
        unique: dict[tuple[int, int, int, int], dict] = {}
        for node in nodes:
            bounds = _bounds(node)
            if node.get("editable") and bounds:
                unique[bounds] = node
        return next(iter(unique.values()), None) if len(unique) == 1 else None

    def _wait_for_unique_editable(self, wait_seconds: float = 4.0) -> tuple[dict, dict | None]:
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 8.0))
        last: dict = {}
        while True:
            last = self._active_ui(include_text=True)
            if last.get("status") != "ok":
                return last, None
            field = self._unique_editable(last.get("nodes") or [])
            if field:
                return last, field
            if time.monotonic() >= deadline:
                return last, None
            time.sleep(0.35)

    def _enter_visible_query(self, value: str, wait_seconds: float = 4.0) -> dict:
        """Paste an explicitly approved search query without selecting a result."""
        query = str(value or "").strip()
        if not query:
            return {"status": "error", "error": "Пустой поисковый запрос"}
        if len(query) > 300:
            return {"status": "error", "error": "Поисковый запрос длиннее 300 символов"}
        snapshot, field = self._wait_for_unique_editable(wait_seconds=wait_seconds)
        if snapshot.get("status") != "ok":
            return snapshot
        if not field:
            return {"status": "error", "error": "Однозначное поле поиска не найдено; ввод остановлен"}
        tapped = self._tap_node(field)
        if tapped.get("status") != "ok":
            return tapped
        copied = self.gateway.set_clipboard(query, confirm=True)
        if copied.get("status") != "ok":
            return copied
        pasted = self.gateway.paste(confirm=True)
        if pasted.get("status") != "ok":
            return pasted
        time.sleep(0.35)
        verified = self._active_ui(include_text=True)
        if verified.get("status") != "ok":
            return verified
        matching = any(
            node.get("editable") and _same_draft_text(node.get("text"), query)
            for node in (verified.get("nodes") or [])
        )
        if not matching:
            return {"status": "error", "error": "Поисковый запрос не подтверждён интерфейсом; выбор результата заблокирован"}
        return {"status": "query_entered", "length": len(query)}

    @staticmethod
    def _label(node: dict) -> str:
        return " ".join(str(node.get(key) or "") for key in ("text", "description", "resource"))

    def _click_target(self, nodes: Iterable[dict], matching: dict) -> dict | None:
        """Return the smallest clickable ancestor of a matching text node."""
        matching_bounds = _bounds(matching)
        if not matching_bounds:
            return None
        options: list[tuple[int, dict]] = []
        for node in nodes:
            node_bounds = _bounds(node)
            if not node_bounds or not node.get("clickable"):
                continue
            if _contains(node_bounds, matching_bounds):
                options.append((_area(node_bounds), node))
        if not options:
            return matching if matching.get("clickable") else None
        options.sort(key=lambda item: item[0])
        return options[0][1]

    def _find_control(self, nodes: list[dict], labels: Iterable[str], *, lower_half: bool = False) -> dict | None:
        wanted = tuple(_fold(value) for value in labels if _fold(value))
        ymax = max((_bounds(node) or (0, 0, 0, 0))[3] for node in nodes) if nodes else 0
        candidates: list[tuple[int, dict]] = []
        for node in nodes:
            bounds = _bounds(node)
            if not bounds:
                continue
            if lower_half and ymax and bounds[1] < ymax // 2:
                continue
            label = _fold(self._label(node))
            if not label or not any(term in label for term in wanted):
                continue
            target = self._click_target(nodes, node)
            if target:
                candidates.append((_area(_bounds(target) or bounds), target))
        if not candidates:
            return None
        # Deduplicate nested nodes that point to exactly the same touch target.
        unique: dict[tuple[int, int, int, int], tuple[int, dict]] = {}
        for area, node in candidates:
            bounds = _bounds(node)
            if bounds and (bounds not in unique or area < unique[bounds][0]):
                unique[bounds] = (area, node)
        return sorted(unique.values(), key=lambda item: item[0])[0][1]

    def open(self, confirm: bool = False) -> dict:
        if not confirm:
            return {"status": "need_confirm", "action": "android_open_app", "package": self.package}
        if not self._available():
            return {"status": "not_installed", "error": f"{self.title} не найден на телефоне"}
        result = self.gateway.open_app(self.package, confirm=True)
        if result.get("status") == "ok":
            result["title"] = self.title
        return result


class MessengerDraftAdapter(ActiveAppAdapter):
    """Draft/send primitive shared by WhatsApp and iMe.

    It does not discover arbitrary chats by itself.  A caller must either use
    WhatsApp's dedicated confirmed chat opener or open the iMe chat manually.
    """

    send_labels = ("отправить", "send", "надіслати", "надіслати")

    def _composer(self, nodes: list[dict]) -> dict | None:
        editable: list[tuple[int, dict]] = []
        for node in nodes:
            bounds = _bounds(node)
            if not bounds or not node.get("editable"):
                continue
            editable.append((bounds[3], node))
        return max(editable, default=(0, None), key=lambda item: item[0])[1]

    def prepare_draft(self, text: str, confirm: bool = False) -> dict:
        body = str(text or "").strip()
        if not body:
            return {"status": "error", "error": "Текст черновика пуст"}
        if len(body) > 3500:
            return {"status": "error", "error": "Черновик длиннее 3500 символов"}
        if not confirm:
            return {"status": "need_confirm", "action": "android_prepare_messenger_draft", "length": len(body)}
        if not self._available():
            return {"status": "not_installed", "error": f"{self.title} не найден на телефоне"}
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        nodes = snapshot.get("nodes") or []
        composer = self._composer(nodes)
        if not composer:
            return {"status": "error", "error": "Поле ввода не найдено; откройте нужный чат на телефоне"}
        tapped = self._tap_node(composer)
        if tapped.get("status") != "ok":
            return tapped
        copied = self.gateway.set_clipboard(body, confirm=True)
        if copied.get("status") != "ok":
            return copied
        pasted = self.gateway.paste(confirm=True)
        if pasted.get("status") != "ok":
            return pasted
        # Give Accessibility a small deterministic chance to update, then
        # verify the exact composer content without ever logging it.
        time.sleep(0.35)
        verified = self._active_ui(include_text=True)
        if verified.get("status") != "ok":
            return verified
        current = self._composer(verified.get("nodes") or [])
        if not current or not _same_draft_text(current.get("text"), body):
            return {
                "status": "error",
                "error": "Черновик не подтверждён интерфейсом; отправка заблокирована",
            }
        lease = self.gateway.begin_control_session(self.package, "messenger_draft", ttl_seconds=300)
        if lease.get("status") != "ok":
            return lease
        draft = self.store.create(
            "messenger_draft", self.package,
            {"text": body, "session_id": lease.get("session_id")}, ttl_seconds=300,
        )
        return {
            "status": "draft_ready",
            "draft_id": draft["id"],
            "expires_at": draft["expires_at"],
            "length": len(body),
        }

    def _send_control(self, nodes: list[dict]) -> dict | None:
        candidate = self._find_control(nodes, self.send_labels, lower_half=True)
        if not candidate:
            return None
        # A visual message body containing the word "send" must never become a
        # button. Require an actual control signal as well.
        resource = _fold(candidate.get("resource"))
        description = _fold(candidate.get("description"))
        text = _fold(candidate.get("text"))
        label_exact = description in self.send_labels or text in self.send_labels
        if not candidate.get("clickable") and "send" not in resource and "отправ" not in resource:
            return None
        if not label_exact and "send" not in resource and "отправ" not in resource and "надісл" not in resource:
            return None
        return candidate

    def send_draft(self, draft_id: str, confirm: bool = False) -> dict:
        draft = self.store.get(draft_id, kind="messenger_draft", package=self.package)
        if not draft:
            return {"status": "expired", "error": "Черновик не найден или истёк"}
        if draft.get("state") != "prepared":
            return {"status": "error", "error": "Этот черновик уже обработан"}
        if not confirm:
            return {"status": "need_confirm", "action": "android_send_messenger_draft", "draft_id": str(draft_id)}
        session_id = str((draft.get("data") or {}).get("session_id") or "")
        lease = self.gateway.validate_control_session(session_id, self.package)
        if lease.get("status") != "ok":
            return lease
        body = str((draft.get("data") or {}).get("text") or "")
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        nodes = snapshot.get("nodes") or []
        composer = self._composer(nodes)
        # Do not send if the user touched the phone, changed chats, or altered
        # even one character after reviewing the draft in Telegram.
        if not composer or not _same_draft_text(composer.get("text"), body):
            return {"status": "draft_changed", "error": "Текст в поле изменился; отправка заблокирована"}
        control = self._send_control(nodes)
        if not control:
            return {"status": "error", "error": "Кнопка отправки не распознана; отправьте вручную на телефоне"}
        tapped = self._tap_node(control)
        if tapped.get("status") != "ok":
            return tapped
        self.store.update(draft_id, state="send_tapped", sent_at=_iso())
        self.gateway.end_control_session(session_id)
        # UI tap is not a network delivery receipt.  Never overstate it.
        return {"status": "send_tapped", "draft_id": str(draft_id)}

    def cancel_draft(self, draft_id: str) -> dict:
        draft = self.store.get(draft_id, kind="messenger_draft", package=self.package)
        if not draft:
            return {"status": "expired", "error": "Черновик не найден или истёк"}
        self.store.update(draft_id, state="cancelled", cancelled_at=_iso())
        self.gateway.end_control_session(str((draft.get("data") or {}).get("session_id") or ""))
        # We deliberately do not clear the on-phone composer: deleting or
        # modifying text is a separate destructive UI action for the owner.
        return {"status": "cancelled", "draft_id": str(draft_id)}

    def read_visible_chat(self, limit: int = 8) -> dict:
        """Return explicitly requested visible messages, with secret masking."""
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        controls = {
            "поиск", "search", "отправить", "send", "надіслати", "назад", "back",
            "камера", "camera", "ещё", "more", "прикрепить", "attach", "микрофон",
            "voice message", "сообщение", "message",
        }
        values: list[str] = []
        seen: set[str] = set()
        for node in snapshot.get("nodes") or []:
            if node.get("editable"):
                continue
            text = " ".join(str(node.get("text") or "").split())
            if len(text) < 2 or len(text) > 700:
                continue
            if _fold(text) in controls:
                continue
            key = _fold(text)
            if key in seen:
                continue
            seen.add(key)
            values.append(_mask_sensitive(text))
        return {"status": "ok", "messages": values[-max(1, min(int(limit), 12)):], "count": len(values)}


class WhatsAppPhoneAdapter(MessengerDraftAdapter):
    package = "com.whatsapp"
    profile = "whatsapp"
    title = "WhatsApp"
    search_labels = ("поиск", "search", "поиск…", "search…")

    def _exact_chat_target(self, nodes: list[dict], contact: str) -> tuple[dict | None, bool]:
        target = _fold(contact)
        candidates: dict[tuple[int, int, int, int], dict] = {}
        for node in nodes:
            # The active search field contains the query too; it is not a chat
            # result and must never be tapped as one.
            if node.get("editable"):
                continue
            # Names normally live in text; description fallback helps across
            # WhatsApp layouts. Exact match avoids opening a similarly named chat.
            fields = (_fold(node.get("text")), _fold(node.get("description")))
            if target not in fields:
                continue
            clickable = self._click_target(nodes, node)
            bounds = _bounds(clickable or node)
            if clickable and bounds:
                candidates[bounds] = clickable
        values = list(candidates.values())
        if len(values) == 1:
            return values[0], False
        return None, len(values) > 1

    def open_chat(self, contact: str, confirm: bool = False) -> dict:
        name = " ".join(str(contact or "").split())
        if not name:
            return {"status": "error", "error": "Укажите имя чата"}
        if len(name) > 100:
            return {"status": "error", "error": "Имя чата слишком длинное"}
        if not confirm:
            return {
                "status": "need_confirm",
                "action": "whatsapp_open_chat",
                "contact": name,
                "warning": "Открытие чата может пометить его как прочитанный",
            }
        opened = self.open(confirm=True)
        if opened.get("status") != "ok":
            return opened
        time.sleep(0.55)
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        nodes = snapshot.get("nodes") or []
        search = self._find_control(nodes, self.search_labels)
        if not search:
            return {"status": "error", "error": "Кнопка поиска WhatsApp не распознана; действие остановлено"}
        tapped = self._tap_node(search)
        if tapped.get("status") != "ok":
            return tapped
        time.sleep(0.2)
        copied = self.gateway.set_clipboard(name, confirm=True)
        if copied.get("status") != "ok":
            return copied
        pasted = self.gateway.paste(confirm=True)
        if pasted.get("status") != "ok":
            return pasted
        time.sleep(0.55)
        results = self._active_ui(include_text=True)
        if results.get("status") != "ok":
            return results
        candidate, ambiguous = self._exact_chat_target(results.get("nodes") or [], name)
        if ambiguous:
            return {"status": "ambiguous", "error": "Найдено несколько чатов с таким точным именем; выберите вручную"}
        if not candidate:
            return {"status": "not_found", "error": "Чат с точным именем не найден; ничего не открыто"}
        selected = self._tap_node(candidate)
        if selected.get("status") != "ok":
            return selected
        return {"status": "opened", "contact": name}


class IMePhoneAdapter(MessengerDraftAdapter):
    package = "com.iMe.android"
    profile = "ime"
    title = "iMe Messenger"


class PhoneAppMonitor(ActiveAppAdapter):
    """Read-only app status and confirmed opening for transport/bank apps."""

    notification_packages: tuple[str, ...] = ()

    def status(self) -> dict:
        base = super().status()
        notices = self.gateway.notifications(limit=60)
        packages = set(self.notification_packages or (self.package,))
        count = sum(1 for item in notices.get("notifications") or [] if item.get("package") in packages)
        # Only counts are returned; notification text can carry OTPs, balances,
        # location and banking data.
        base["notification_count"] = count
        calibration = self.calibrations.get(self.profile)
        if calibration.get("package") == self.package:
            base["ui_calibrated"] = True
            base["route_controls"] = dict(calibration.get("selectors") or {})
        return base


class UklonPhoneAdapter(PhoneAppMonitor):
    package = "ua.com.uklontaxi"
    profile = "uklon"
    title = "Uklon Passenger"
    notification_packages = ("ua.com.uklontaxi", "ua.com.uklon.uklondriver")
    driver_package = "ua.com.uklon.uklondriver"
    pickup_resource = "buttonPickUpAddress"
    destination_resource = "buttonDropOffAddress"

    def _resource_control(self, nodes: list[dict], resource_name: str) -> dict | None:
        matches = [node for node in nodes if str(node.get("resource") or "").endswith(resource_name)]
        targets: dict[tuple[int, int, int, int], dict] = {}
        for node in matches:
            target = self._click_target(nodes, node) or (node if node.get("clickable") else None)
            bounds = _bounds(target or {})
            if target and bounds:
                targets[bounds] = target
        return next(iter(targets.values()), None) if len(targets) == 1 else None

    def _calibration_selectors(self, nodes: list[dict]) -> dict[str, bool]:
        return {
            "pickup_address": bool(self._resource_control(nodes, self.pickup_resource)),
            "destination_address": bool(self._resource_control(nodes, self.destination_resource)),
        }

    def calibrate(self, confirm: bool = False, wait_seconds: float = 12.0) -> dict:
        # Passenger cold-starts can take several seconds before Compose exposes
        # address controls; a shorter generic UI wait would cache splash data.
        return super().calibrate(confirm=confirm, wait_seconds=wait_seconds)

    def open_driver(self, confirm: bool = False) -> dict:
        if not confirm:
            return {"status": "need_confirm", "action": "android_open_app", "package": self.driver_package}
        installed = self.gateway.apps(limit=2000).get("apps") or []
        if self.driver_package not in installed:
            return {"status": "not_installed", "error": "Uklon Driver не найден на телефоне"}
        result = self.gateway.open_app(self.driver_package, confirm=True)
        if result.get("status") == "ok":
            result["title"] = "Uklon Driver"
        return result

    def stage_route(self, pickup: str, destination: str, confirm: bool = False) -> dict:
        """Store a private route draft and verify Passenger controls. No order is created."""
        start, end = " ".join(str(pickup or "").split()), " ".join(str(destination or "").split())
        if not end:
            return {"status": "error", "error": "Укажите пункт назначения"}
        if not confirm:
            return {"status": "need_confirm", "action": "uklon_stage_route", "has_pickup": bool(start), "has_destination": True}
        opened = self.open(confirm=True)
        if opened.get("status") != "ok":
            return opened
        snapshot, selectors = self._wait_for_calibrated_ui(wait_seconds=12.0)
        if snapshot.get("status") != "ok":
            return snapshot
        self._save_calibration(snapshot, selectors)
        # Do not guess address suggestions or touch a booking control. Selecting
        # a place and creating a ride remain deliberate follow-up actions.
        draft = self.store.create("route_draft", self.package, {"pickup": start, "destination": end}, ttl_seconds=600)
        return {
            "status": "route_staged", "route_id": draft["id"], "expires_at": draft["expires_at"],
            "booking": "not_created", "controls": selectors,
        }

    def prepare_address_query(self, route_id: str, field: str, confirm: bool = False) -> dict:
        """Type one approved route query, but never choose a suggestion or order a ride."""
        draft = self.store.get(route_id, kind="route_draft", package=self.package)
        if not draft:
            return {"status": "expired", "error": "Черновик маршрута не найден или истёк"}
        key = str(field or "").casefold()
        mapping = {
            "pickup": ("pickup", self.pickup_resource),
            "destination": ("destination", self.destination_resource),
        }
        if key not in mapping:
            return {"status": "error", "error": "Поле маршрута должно быть pickup или destination"}
        data_key, resource = mapping[key]
        value = str((draft.get("data") or {}).get(data_key) or "").strip()
        if not value:
            return {"status": "error", "error": "Для этого поля нет поискового запроса"}
        if not confirm:
            return {"status": "need_confirm", "action": "uklon_enter_route_query", "route_id": str(route_id), "field": key}
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        trigger = self._resource_control(snapshot.get("nodes") or [], resource)
        if not trigger:
            return {"status": "error", "error": "Элемент адреса Uklon не распознан; ввод остановлен"}
        opened = self._tap_node(trigger)
        if opened.get("status") != "ok":
            return opened
        entered = self._enter_visible_query(value, wait_seconds=5.0)
        if entered.get("status") != "query_entered":
            return entered
        self.store.update(route_id, state=f"{key}_query_entered", last_field=key, entered_at=_iso())
        return {"status": "query_entered", "route_id": str(route_id), "field": key}


class EasyWayPhoneAdapter(PhoneAppMonitor):
    package = "com.eway"
    profile = "easyway"
    title = "EasyWay"
    destination_labels = ("куда", "куди", "destination", "where to", "пункт назначения")

    def _destination_trigger(self, nodes: list[dict]) -> dict | None:
        candidates: list[dict] = []
        for node in nodes:
            bounds = _bounds(node)
            if not bounds or not node.get("clickable"):
                continue
            # EasyWay currently exposes the destination field as a top Button.
            # Requiring both role and position avoids treating map pins as input.
            if not str(node.get("class") or "").endswith("Button") or bounds[1] > 300:
                continue
            label = _fold(self._label(node))
            if any(term in label for term in self.destination_labels):
                candidates.append(node)
        unique = {bounds: node for node in candidates if (bounds := _bounds(node))}
        return next(iter(unique.values()), None) if len(unique) == 1 else None

    def _calibration_selectors(self, nodes: list[dict]) -> dict[str, bool]:
        return {"destination_trigger": bool(self._destination_trigger(nodes))}

    def stage_route(self, destination: str, confirm: bool = False) -> dict:
        place = " ".join(str(destination or "").split())
        if not place:
            return {"status": "error", "error": "Укажите остановку или пункт назначения"}
        if not confirm:
            return {"status": "need_confirm", "action": "easyway_stage_route", "has_destination": True}
        opened = self.open(confirm=True)
        if opened.get("status") != "ok":
            return opened
        snapshot, selectors = self._wait_for_calibrated_ui(wait_seconds=4.5)
        if snapshot.get("status") != "ok":
            return snapshot
        self._save_calibration(snapshot, selectors)
        draft = self.store.create("transit_route_draft", self.package, {"destination": place}, ttl_seconds=600)
        return {"status": "route_staged", "route_id": draft["id"], "expires_at": draft["expires_at"], "controls": selectors}

    def prepare_destination_query(self, route_id: str, confirm: bool = False) -> dict:
        """Type an approved EasyWay query, leaving route/result selection manual."""
        draft = self.store.get(route_id, kind="transit_route_draft", package=self.package)
        if not draft:
            return {"status": "expired", "error": "Черновик маршрута не найден или истёк"}
        value = str((draft.get("data") or {}).get("destination") or "").strip()
        if not value:
            return {"status": "error", "error": "Для маршрута нет поискового запроса"}
        if not confirm:
            return {"status": "need_confirm", "action": "easyway_enter_route_query", "route_id": str(route_id)}
        snapshot = self._active_ui(include_text=True)
        if snapshot.get("status") != "ok":
            return snapshot
        trigger = self._destination_trigger(snapshot.get("nodes") or [])
        if not trigger:
            return {"status": "error", "error": "Поле маршрута EasyWay не распознано; ввод остановлен"}
        opened = self._tap_node(trigger)
        if opened.get("status") != "ok":
            return opened
        entered = self._enter_visible_query(value, wait_seconds=5.0)
        if entered.get("status") != "query_entered":
            return entered
        self.store.update(route_id, state="destination_query_entered", entered_at=_iso())
        return {"status": "query_entered", "route_id": str(route_id), "field": "destination"}


class BankPhoneAdapter(PhoneAppMonitor):
    """Bank apps deliberately expose no balance/transfer/OTP workflow."""

    def banking_policy(self) -> dict:
        status = self.status()
        status["policy"] = "Только уведомления, статус и подтверждаемое открытие. Платежи, OTP, карты и биометрия недоступны."
        return status


class ABankPhoneAdapter(BankPhoneAdapter):
    package = "ua.com.abank"
    profile = "abank"
    title = "A-Bank"


class Privat24PhoneAdapter(BankPhoneAdapter):
    package = "ua.privatbank.ap24"
    profile = "privat24"
    title = "Privat24"


def adapter_for(name: str, gateway: AndroidGateway) -> ActiveAppAdapter | None:
    key = _fold(name).replace(" ", "")
    mapping = {
        "whatsapp": WhatsAppPhoneAdapter,
        "ватсап": WhatsAppPhoneAdapter,
        "watsapp": WhatsAppPhoneAdapter,
        "ime": IMePhoneAdapter,
        "imemessenger": IMePhoneAdapter,
        "uklon": UklonPhoneAdapter,
        "easyway": EasyWayPhoneAdapter,
        "eway": EasyWayPhoneAdapter,
        "abank": ABankPhoneAdapter,
        "a-bank": ABankPhoneAdapter,
        "privat24": Privat24PhoneAdapter,
    }
    cls = mapping.get(key)
    return cls(gateway) if cls else None
