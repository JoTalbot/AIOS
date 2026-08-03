"""Autonomy Journal — аудит-след решений автономии.

Каждое решение записывается строкой JSONL в ``data/autonomy_log.jsonl``.
Формат строки:
    {ts, platform, chat, user, intent, action, params, decision, reason, result}
Секреты и текст платежей/токенов НЕ логируются.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Journal:
    def __init__(self, path: Path | None = None):
        self.path = path or PROJECT_ROOT / "data" / "autonomy_log.jsonl"

    def log(self, **fields: Any) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            rec.update(fields)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass  # журнал не должен ронять основную петлю

    def summary(self, n: int = 200) -> dict:
        """Агрегированная статистика по последним n решениям."""
        counts: dict[str, int] = {}
        by_action: dict[str, dict] = {}
        rows = []
        try:
            if self.path.exists():
                for line in self.path.read_text(encoding="utf-8").splitlines()[-n:]:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            pass
        for r in rows:
            d = r.get("decision", "?")
            counts[d] = counts.get(d, 0) + 1
            a = r.get("action", "?")
            b = by_action.setdefault(a, {"total": 0, "auto": 0, "esc": 0, "manual": 0, "blocked": 0})
            b["total"] += 1
            if d in b:
                b[d] += 1
        return {
            "total": len(rows),
            "by_decision": counts,
            "by_action": by_action,
        }
