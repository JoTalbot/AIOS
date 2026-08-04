"""DeviceSupervisor — умный супервизор соединения с Android-телефоном.

Чем отличается от старого watchdog (aios-android-gateway.service):

* экспоненциальный backoff вместо спама `adb connect` каждые 30 секунд;
* успешность connect определяется последующим probe (adb connect возвращает
  код 0 даже при «Connection refused» — старый цикл считал это успехом);
* состояние (offline_since, backoff, эскалация) переживает рестарт демона;
* circuit breaker для Companion: повторные сбои помечают его «сломанным»,
  и задачи, требующие Companion, откладываются вместо гарантированного фейла;
* эскалация (пока — событие; далее reaction engine отправит алерт в Telegram).
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

from aios_core.android_gateway import AndroidGateway
from aios_core.phone_brain.common import iso, parse_iso, read_json, utc_now, write_json

DEFAULTS: dict[str, Any] = {
    "fail_streak": 0,
    "interval": 0,
    "next_attempt": "",
    "offline_since": "",
    "escalated": False,
    "last_error": "",
    "companion_streak": 0,
    "companion_broken": False,
}


class DeviceSupervisor:
    """Один цикл poll() = status → (connect + probe при offline, с backoff)."""

    def __init__(self, root: Path | str, gateway: AndroidGateway | None = None, *,
                 min_interval: int = 30, max_interval: int = 900, factor: float = 2.0,
                 escalate_after_seconds: int = 600, companion_fail_limit: int = 3,
                 state_path: Path | str | None = None, events: Any = None,
                 now_fn: Callable[[], Any] = utc_now):
        self.root = Path(root)
        self.gateway = gateway if gateway is not None else AndroidGateway(self.root)
        self.min_interval = max(5, int(min_interval))
        self.max_interval = max(self.min_interval, int(max_interval))
        self.factor = max(1.1, float(factor))
        self.escalate_after_seconds = max(60, int(escalate_after_seconds))
        self.companion_fail_limit = max(1, int(companion_fail_limit))
        self.state_path = (Path(state_path) if state_path
                           else self.root / "data" / "android_gateway" / "brain_supervisor.json")
        self.events = events
        self._now = now_fn  # в тестах подменяется контролируемыми часами
        self.last_health: dict = {}

    # ------------------------------------------------------------- helpers

    def _state(self) -> dict:
        state = dict(DEFAULTS)
        state.update(read_json(self.state_path, {}))
        return state

    def _save(self, state: dict) -> None:
        write_json(self.state_path, state)

    def _event(self, event_type: str, data: dict) -> None:
        if self.events is not None:
            try:
                self.events.append(event_type, data)
            except Exception:
                pass

    @staticmethod
    def _connected(status: dict) -> bool:
        return bool(status.get("connected")) and status.get("status") == "ok"

    @staticmethod
    def _companion_ok(status: dict) -> bool:
        companion = status.get("companion")
        if not isinstance(companion, dict):
            return False
        return companion.get("connected") is True or companion.get("status") == "ok"

    # --------------------------------------------------------------- probes

    def is_online(self) -> bool:
        """Быстрый ответ из свежего кэша; иначе один probe напрямую."""
        checked = parse_iso((self.last_health.get("device") or {}).get("checked_at"))
        if checked and (self._now() - checked).total_seconds() < 45:
            return self._connected(self.last_health.get("device") or {})
        try:
            return self._connected(self.gateway.status())
        except Exception:
            return False

    def companion_ready(self) -> bool:
        """Готовность Companion по кэшу/прямому статусу (гейт для UI-задач)."""
        try:
            status = (self.last_health.get("device") if self.last_health else {}) or self.gateway.status()
            if (self._state().get("companion_broken")):
                return False
            return self._companion_ok(status)
        except Exception:
            return False

    def health(self) -> dict:
        """Кэшированный health для API (без лишних ADB-вызовов)."""
        if self.last_health:
            return self.last_health
        return {"status": "unknown", "note": "устройство ещё не опрошено"}

    # ----------------------------------------------------------------- poll

    def poll(self) -> dict:
        """Цикл супервизора. Обновляет health.json в прежней схеме (gateway.status
        сам его пишет — совместимость с существующими потребителями сохранена)."""
        now = self._now()
        try:
            status = self.gateway.status()
        except Exception as exc:  # не роняем демона из-за сбоя ADB-подпроцесса
            status = {"status": "error", "connected": False, "error": str(exc)[:200]}
        state = self._state()
        connected = self._connected(status)
        brain: dict[str, Any] = {"checked_at": iso(now)}

        if status.get("status") == "unregistered":
            brain["note"] = "unregistered"
            self.last_health = {"status": "unregistered", "device": status, "brain": brain}
            return self.last_health

        if connected:
            if state.get("offline_since"):
                self._event("device_online", {"was_offline_since": state["offline_since"]})
            state.update(fail_streak=0, interval=0, next_attempt="", offline_since="",
                         escalated=False, last_error="")
            companion_ok = self._companion_ok(status)
            state["companion_streak"] = 0 if companion_ok else int(state.get("companion_streak") or 0) + 1
            state["companion_broken"] = (not companion_ok) and state["companion_streak"] >= self.companion_fail_limit
            brain.update(backoff="idle", companion_broken=state["companion_broken"])
        else:
            offline_since = state.get("offline_since") or iso(now)
            state["offline_since"] = offline_since
            start = parse_iso(offline_since) or now
            downtime = max(0, int((now - start).total_seconds()))
            if downtime >= self.escalate_after_seconds and not state.get("escalated"):
                self._event("device_offline_escalated",
                            {"offline_seconds": downtime, "serial": status.get("serial")})
                state["escalated"] = True
            attempt_at = parse_iso(state.get("next_attempt"))
            if attempt_at is None or now >= attempt_at:
                reconnect = self._attempt_reconnect(state)
                if reconnect is not None and self._connected(reconnect):
                    # восстановились в этом же цикле
                    self._event("device_online", {"was_offline_since": offline_since})
                    state.update(fail_streak=0, interval=0, next_attempt="", offline_since="",
                                 escalated=False, last_error="")
                    companion_ok = self._companion_ok(reconnect)
                    state["companion_streak"] = 0 if companion_ok else int(state.get("companion_streak") or 0) + 1
                    state["companion_broken"] = (not companion_ok) and state["companion_streak"] >= self.companion_fail_limit
                    status = reconnect
                    brain.update(backoff="recovered", companion_broken=state["companion_broken"])
                    connected = True
            if not connected:
                brain.update(offline_seconds=downtime,
                             backoff_seconds=int(state.get("interval") or 0),
                             next_attempt=state.get("next_attempt") or "",
                             fail_streak=int(state.get("fail_streak") or 0),
                             escalated=bool(state.get("escalated")),
                             last_error=state.get("last_error") or "")

        self._save(state)
        self.last_health = {"status": "ok" if connected else "offline",
                            "device": status, "brain": brain}
        return self.last_health

    def _attempt_reconnect(self, state: dict) -> dict | None:
        """connect + обязательный probe. При неудаче наращивает backoff.
        Мутирует переданный state; сохранение — единожды в poll()."""
        try:
            result = self.gateway.connect()
        except Exception as exc:
            result = {"status": "error", "message": str(exc)[:200]}
        try:
            probe = self.gateway.status()
        except Exception:
            probe = {"status": "error", "connected": False}
        if self._connected(probe):
            return probe
        fail_streak = int(state.get("fail_streak") or 0) + 1
        previous = int(state.get("interval") or 0)
        interval = min(self.max_interval,
                       max(self.min_interval, int(previous * self.factor) if previous else self.min_interval))
        state.update(fail_streak=fail_streak, interval=interval,
                     next_attempt=iso(self._now() + timedelta(seconds=interval)),
                     last_error=str(result.get("message") or result.get("error") or "")[:160])
        return None
