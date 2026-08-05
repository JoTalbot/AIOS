#!/usr/bin/env python3
"""
AIOS Analytics Snapshots — раз в день сохраняет метрики аккаунтов
(подписчики Instagram/TikTok, объявления OLX) в data/analytics_state.json.
По ним бот показывает динамику: «аналитика», «рост подписчиков».

Запуск по systemd-таймеру (раз в день).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "analytics_state.json"


def _instagram_phone() -> dict:
    """Метрики Instagram из мобильного приложения на телефоне G1 (fallback,
    когда браузерная сессия недоступна). Читает только свой профиль."""
    import re as _re
    import time as _time
    try:
        from aios_core.android_gateway import AndroidGateway
        gw = AndroidGateway(ROOT)
        if gw.open_app("com.instagram.android", confirm=True).get("status") != "ok":
            return {}
        _time.sleep(5)

        def nodes():
            return gw.ui_snapshot(confirm=True, include_text=True).get("nodes") or []

        def find(pred):
            return next((n for n in nodes() if pred(n)), None)

        prof = find(lambda n: (n.get("description") or "") in ("Профиль", "Профіль", "Profile")
                    or (n.get("text") or "") in ("Профиль", "Профіль"))
        if prof:
            b = prof["bounds"]
            gw.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, confirm=True)
            _time.sleep(4)
        out = {}
        for n in nodes():
            blob = (n.get("text") or "") + " " + (n.get("description") or "")
            m = _re.search(r"(\d[\d\s]{0,6})\s*подписчики", blob, _re.IGNORECASE)
            if m:
                out["instagram_followers"] = int(m.group(1).replace(" ", ""))
            m = _re.search(r"(\d[\d\s]{0,6})\s*подписки", blob, _re.IGNORECASE)
            if m:
                out["instagram_following"] = int(m.group(1).replace(" ", ""))
        return out
    except Exception:
        return {}


def _run_ac(args, timeout=170) -> dict:
    py = "/opt/aios/.venv/bin/python"
    needs_x = True
    if len(args) >= 2 and args[0] == "google" and args[1] in ("gmail_list", "gmail_send", "gmail_search", "open"):
        needs_x = False
    if len(args) >= 2 and args[0] == "tg":
        needs_x = False
    cmd = (["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, str(ROOT / "run_account_control.py")] + args) \
        if needs_x else ([py, str(ROOT / "run_account_control.py")] + args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        out = (r.stdout or "").strip()
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-300:]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def collect() -> dict:
    """Собрать текущие метрики."""
    today = datetime.now().strftime("%Y-%m-%d")
    metrics = {"date": today}

    # Instagram: сначала браузерная сессия, fallback — приложение на телефоне
    try:
        ig = _run_ac(["instagram", "profile"])
        if ig.get("status") == "ok":
            p = ig.get("profile", {})
            metrics["instagram_followers"] = p.get("followers")
            metrics["instagram_following"] = p.get("following")
    except Exception:
        pass
    if metrics.get("instagram_followers") is None:
        metrics.update(_instagram_phone())

    # TikTok
    try:
        tt = _run_ac(["tiktok", "profile"])
        if tt.get("status") == "ok":
            p = tt.get("tiktok", {})
            metrics["tiktok_followers"] = p.get("followers")
            metrics["tiktok_following"] = p.get("following")
            metrics["tiktok_likes"] = p.get("likes")
    except Exception:
        pass

    # OLX
    try:
        olx = _run_ac(["olx", "profile"])
        if olx.get("status") == "ok":
            o = olx.get("olx", {})
            metrics["olx_ads"] = o.get("ads_count")
    except Exception:
        pass

    return metrics


def main() -> int:
    metrics = collect()
    # загружаем историю
    try:
        history = json.loads(STATE.read_text())
    except Exception:
        history = {}
    if not isinstance(history, dict):
        history = {}
    history[metrics["date"]] = metrics
    # оставляем последние 90 дней
    dates = sorted(history.keys())
    for d in dates[:-90]:
        history.pop(d, None)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    print(f"Снапшот сохранён: {metrics}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
