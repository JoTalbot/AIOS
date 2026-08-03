"""Autonomy State — память сессий по клиентам, дедупликация, доверие.

Хранит сессию каждого клиента: последнее сообщение, историю торга,
предлагаемые цены, доверие (new/known/trusted), ссылки на активные сделки.
Данные персистятся в ``data/autonomy_sessions/<platform>__<chat>.json``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Session:
    def __init__(self, platform: str, chat: str, data: dict):
        self.platform = platform
        self.chat = chat
        self.data = data

    @property
    def trust(self) -> str:
        return self.data.get("trust", "new")

    def mark_known(self) -> None:
        if self.data.get("trust", "new") == "new":
            self.data["trust"] = "known"

    @property
    def reputation(self) -> int:
        """Числовая репутация клиента (старт 0)."""
        return int(self.data.get("reputation", 0))

    def adjust_reputation(self, delta: int) -> None:
        """Уменьшить/увеличить репутацию клиента (анти-скам)."""
        cur = int(self.data.get("reputation", 0)) + delta
        self.data["reputation"] = max(-20, min(20, cur))
        # trust по репутации
        if self.data["reputation"] >= 3:
            self.data["trust"] = "trusted"
        elif self.data["reputation"] <= -5:
            self.data["trust"] = "risky"
        self.data["reputation_history"] = self.data.get("reputation_history", []) + [delta]

    @property
    def last_seen_msg(self) -> str:
        return self.data.get("last_seen_msg", "")

    @property
    def rounds(self) -> int:
        return int(self.data.get("rounds", 0))

    @property
    def last_offer(self) -> float | None:
        v = self.data.get("last_offer")
        return float(v) if isinstance(v, (int, float)) else None


class StateStore:
    """Хранилище сессий клиентов (JSON-файлы)."""

    def __init__(self, root: Path | None = None):
        self.root = root or PROJECT_ROOT
        self.dir = self.root / "data" / "autonomy_sessions"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, platform: str, chat: str) -> Path:
        safe = f"{platform}__{chat}".replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.dir / f"{safe}.json"

    def get(self, platform: str, chat: str) -> Session:
        path = self._path(platform, chat)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        return Session(platform, chat, data)

    def save(self, s: Session) -> None:
        s.data["updated"] = _now()
        self._path(s.platform, s.chat).write_text(
            json.dumps(s.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def note_message(self, platform: str, chat: str, msg_id: str, text: str) -> Session:
        s = self.get(platform, chat)
        if s.last_seen_msg == msg_id:
            return s  # дедупликация: уже видели
        s.data["last_seen_msg"] = msg_id
        s.data["last_text"] = text[:500]
        s.data["last_ts"] = _now()
        s.data["rounds"] = int(s.data.get("rounds", 0)) + 1
        self.save(s)
        return s

    def set_last_offer(self, s: Session, offer: float) -> None:
        s.data["last_offer"] = float(offer)
        self.save(s)

    def record_sale(self, s: Session, item: str, amount: float) -> None:
        s.data["last_sale"] = {"item": item, "amount": amount, "ts": _now()}
        s.data["trust"] = "trusted"
        self.save(s)
