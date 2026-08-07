#!/usr/bin/env python3
"""AIOS Converge + Kernel API — Stitch messenger hub & operator dashboard."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, "/root/AIOS")
sys.path.insert(0, "/root/AIOS/converge")
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(os.environ.get("AIOS_ROOT", "/root/AIOS")).resolve()
DATA = ROOT / "data"
STATIC = Path(__file__).resolve().parent / "static"
KERNEL_STATIC = Path(__file__).resolve().parent / "kernel_static"

app = FastAPI(title="AIOS Converge", version="2.0.0", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CHANNEL_META = {
    "tg": {"label": "Telegram", "icon": "send", "color": "#2AABEE"},
    "telegram": {"label": "Telegram", "icon": "send", "color": "#2AABEE"},
    "olx": {"label": "OLX", "icon": "storefront", "color": "#002F34"},
    "ig": {"label": "Instagram", "icon": "photo_camera", "color": "#E4405F"},
    "instagram": {"label": "Instagram", "icon": "photo_camera", "color": "#E4405F"},
    "messenger": {"label": "Messenger", "icon": "chat", "color": "#0084FF"},
    "facebook": {"label": "Facebook", "icon": "chat", "color": "#0084FF"},
    "fb": {"label": "Facebook", "icon": "chat", "color": "#0084FF"},
    "viber": {"label": "Viber", "icon": "call", "color": "#7360F2"},
    "whatsapp": {"label": "WhatsApp", "icon": "chat", "color": "#25D366"},
    "wa": {"label": "WhatsApp", "icon": "chat", "color": "#25D366"},
    "signal": {"label": "Signal", "icon": "lock", "color": "#3A76F0"},
    "android": {"label": "Android", "icon": "smartphone", "color": "#3DDC84"},
    "ime": {"label": "iMe", "icon": "send", "color": "#2AABEE"},
    "approval": {"label": "AIOS", "icon": "smart_toy", "color": "#00f0ff"},
    "crm": {"label": "CRM", "icon": "badge", "color": "#007aff"},
    "sale": {"label": "Сделка", "icon": "local_shipping", "color": "#34C759"},
}

OUTBOX_FILE = DATA / "converge_outbox.json"
SEND_LOG_FILE = DATA / "converge_send_log.jsonl"
THREAD_CACHE = DATA / "converge_thread_cache.json"
PENDING_SENDS: dict[str, dict] = {}
PENDING_TTL_SEC = 600
DEFAULT_TEMPLATES = [
    {"id": "in_stock", "title": "В наличии", "text": "Добрый день! Да, в наличии. Могу отправить Новой Почтой сегодня/завтра."},
    {"id": "price", "title": "Цена", "text": "Добрый день! Актуальная цена — уточню по состоянию. Вам на какой автомобиль?"},
    {"id": "ttn", "title": "ТТН", "text": "Отправил Новой Почтой. Номер ТТН пришлю сразу после оформления. Напишите ФИО, телефон и отделение."},
    {"id": "photo", "title": "Фото", "text": "Сейчас пришлю фото детали с наших ракурсов."},
    {"id": "wait", "title": "Минуту", "text": "Минуту, проверю на складе и вернусь с точным ответом."},
    {"id": "thanks", "title": "Спасибо", "text": "Спасибо за заказ! Если будут вопросы по установке — пишите."},
]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default if default is not None else {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def _write_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _cid(channel: str, ref: str) -> str:
    return hashlib.sha1(f"{channel}|{ref}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _fmt_time(value: str | None) -> str:
    if not value:
        return ""
    s = str(value).strip()
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        return s
    try:
        s2 = s.replace("Z", "+00:00")
        if " " in s2 and "T" not in s2:
            s2 = s2.replace(" ", "T", 1)
        return datetime.fromisoformat(s2[:25]).strftime("%H:%M")
    except Exception:
        return s[:16]


def _load_outbox() -> list[dict]:
    data = _read_json(OUTBOX_FILE, [])
    return data if isinstance(data, list) else []


def _save_outbox(items: list[dict]) -> None:
    _write_json(OUTBOX_FILE, items[-500:])


def _append_send_log(entry: dict) -> None:
    try:
        SEND_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SEND_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _purge_pending() -> None:
    now = time.time()
    for k, v in list(PENDING_SENDS.items()):
        if now - float(v.get("ts") or 0) > PENDING_TTL_SEC:
            PENDING_SENDS.pop(k, None)


def _run_account_control(args: list[str], timeout: int = 160) -> dict:
    py = "/opt/aios/.venv/bin/python"
    helper = str(ROOT / "run_account_control.py")
    if args and args[0] in ("viber", "signal"):
        needs_x = False
    else:
        needs_x = not (
            len(args) >= 2
            and args[0] == "google"
            and args[1] in ("gmail_list", "gmail_send", "gmail_search", "open")
        )
    cmd = (["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, helper] + args) if needs_x else [py, helper] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT), env=os.environ.copy())
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout: канал занят или браузер не ответил"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:240]}
    out_txt = (r.stdout or "").strip()
    if not out_txt:
        return {"status": "error", "error": ((r.stderr or "empty")[-400:])}
    try:
        start = out_txt.find("{")
        return json.loads(out_txt[start:]) if start >= 0 else {"status": "error", "error": out_txt[-400:]}
    except Exception:
        return {"status": "error", "error": out_txt[-400:]}


def _unit_active(unit: str) -> str:
    try:
        r = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=3)
        return (r.stdout or "unknown").strip()
    except Exception:
        return "unknown"


def _inbox_items() -> tuple[list[dict], str]:
    cache = _read_json(DATA / "inbox_cache.json", {})
    items = cache.get("items") if isinstance(cache, dict) else []
    if not isinstance(items, list):
        items = []
    updated = str(cache.get("updated_at") or "") if isinstance(cache, dict) else ""
    return items, updated


def _build_chats(channel: str | None = None, q: str | None = None, unread_only: bool = False) -> list[dict]:
    items, _ = _inbox_items()
    chats: list[dict] = []
    seen: set[str] = set()

    def add(ch: str, ref: str, title: str, preview: str, unread: bool, date: str = "", source: str = "inbox", **extra):
        nonlocal chats
        cid = _cid(ch, ref)
        if cid in seen:
            return
        if channel and channel.lower() not in ("all", ""):
            if ch != channel.lower() and CHANNEL_META.get(ch, {}).get("label", "").lower() != channel.lower():
                return
        if unread_only and not unread:
            return
        if q:
            blob = f"{title} {preview} {ch}".casefold()
            if q.casefold() not in blob:
                return
        meta = CHANNEL_META.get(ch, {"label": ch.upper(), "icon": "forum", "color": "#8b91a0"})
        row = {
            "id": cid, "channel": ch, "channel_label": meta["label"], "icon": meta["icon"], "color": meta["color"],
            "ref": ref, "title": title, "preview": (preview or "")[:160], "unread": unread,
            "date": _fmt_time(date), "source": source, "initials": _initials(title), **extra,
        }
        chats.append(row)
        seen.add(cid)

    for it in items:
        if not isinstance(it, dict):
            continue
        ch = str(it.get("channel") or "unknown").lower()
        title = str(it.get("title") or it.get("ref") or "Без имени").strip()
        ref = str(it.get("ref") or title)
        add(ch, ref, title, str(it.get("preview") or ""), bool(it.get("unread")), str(it.get("date") or ""), service=bool(it.get("service")))

    crm = _read_json(DATA / "customer_crm.json", [])
    if isinstance(crm, list):
        for c in crm:
            if not isinstance(c, dict):
                continue
            name = str(c.get("display_name") or c.get("id") or "Клиент")
            chs = c.get("channels") or ["crm"]
            ch = str(chs[0]).lower()
            add(ch, str(c.get("id") or name), name, f"{c.get('last_status') or 'CRM'} · {c.get('last_item') or ''}",
                bool(c.get("active_count")), str(c.get("updated_at") or ""), "crm",
                phone_masked=c.get("phone_masked"), tags=c.get("tags") or [])

    olx_state = _read_json(DATA / "olx_chat_alerts_state.json", {})
    seen_olx = olx_state.get("seen") if isinstance(olx_state, dict) else {}
    if isinstance(seen_olx, dict):
        for name in seen_olx:
            add("olx", str(name), str(name), "OLX чат · есть активность", True, "", "olx_alerts")

    approvals = _read_json(DATA / "autonomy_approvals.json", [])
    if isinstance(approvals, list):
        pending = [a for a in approvals if isinstance(a, dict) and a.get("status") == "pending"
                   and "stress_" not in str((a.get("proposal") or {}).get("chat") or "")][-15:]
        for a in reversed(pending):
            prop = a.get("proposal") or {}
            chat = str(prop.get("chat") or a.get("id") or "approval")
            add("approval", str(a.get("id")), f"Черновик: {chat}",
                str(a.get("reason") or prop.get("action") or "Требует подтверждения"),
                True, str(a.get("ts") or ""), "approvals",
                approval_id=a.get("id"), verdict=a.get("verdict"), platform=prop.get("platform"))

    # === Старые переписки из threads_index.json и inbox_archive.json (Stitch: показывать не только новые) ===
    try:
        idx = _read_json(DATA / "threads_index.json", {})
        if isinstance(idx, dict):
            for cid_key, meta in idx.items():
                if not isinstance(meta, dict):
                    continue
                ch = str(meta.get("channel") or "viber").lower()
                ref = str(meta.get("ref") or meta.get("title") or "")
                title = str(meta.get("title") or ref or "Без имени")
                if not ref or cid_key in seen:
                    continue
                preview = str(meta.get("preview") or "")
                if not preview:
                    try:
                        thr = _read_json(DATA / "threads" / f"{cid_key}.json", [])
                        if isinstance(thr, list) and thr:
                            last = thr[-1] if isinstance(thr[-1], dict) else {}
                            preview = str(last.get("text") or "")[:120]
                    except Exception:
                        pass
                add(ch, ref, title, preview, False, str(meta.get("updated_at") or ""), "threads")
    except Exception:
        pass
    try:
        t_cache = _read_json(THREAD_CACHE, {})
        if isinstance(t_cache, dict):
            for cid_key, row in t_cache.items():
                if cid_key in seen:
                    continue
                if not isinstance(row, dict):
                    continue
                msgs = row.get("messages") or []
                if not isinstance(msgs, list) or not msgs:
                    continue
                preview = ""
                if msgs:
                    last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                    preview = str(last.get("text") or "")[:120]
                pass
    except Exception:
        pass

    chats.sort(key=lambda c: (not c.get("unread"), c.get("title") or ""))
    return chats


def _build_contacts(channel: str | None = None, q: str | None = None) -> list[dict]:
    contacts: dict[str, dict] = {}

    def upsert(name: str, ch: str, status: str = "", extra: dict | None = None):
        key = name.casefold().strip()
        if not key:
            return
        if q and q.casefold() not in f"{name} {status}".casefold():
            if not (extra and q.casefold() in json.dumps(extra, ensure_ascii=False).casefold()):
                if key not in contacts:
                    return
        if channel and channel.lower() not in ("all", ""):
            if ch.lower() != channel.lower() and CHANNEL_META.get(ch, {}).get("label", "").lower() != channel.lower():
                if key not in contacts:
                    return
        meta = CHANNEL_META.get(ch, {"label": ch, "icon": "person", "color": "#8b91a0"})
        if key not in contacts:
            contacts[key] = {
                "id": _cid(ch, name), "name": name, "initials": _initials(name),
                "channels": [ch], "channel_labels": [meta["label"]], "status": status,
                "color": meta["color"], "icon": meta["icon"],
            }
            if extra:
                contacts[key].update(extra)
        else:
            cur = contacts[key]
            if ch not in cur["channels"]:
                cur["channels"].append(ch)
                cur["channel_labels"].append(meta.get("label", ch))
            if status and not cur.get("status"):
                cur["status"] = status
            if extra:
                for k, v in extra.items():
                    if v and not cur.get(k):
                        cur[k] = v

    for it in _inbox_items()[0]:
        if not isinstance(it, dict):
            continue
        ch = str(it.get("channel") or "").lower()
        if ch in ("android", "approval"):
            continue
        upsert(str(it.get("title") or it.get("ref") or "").strip(), ch, "Active now" if it.get("unread") else "")

    crm = _read_json(DATA / "customer_crm.json", [])
    if isinstance(crm, list):
        for c in crm:
            if not isinstance(c, dict):
                continue
            chs = c.get("channels") or ["crm"]
            upsert(str(c.get("display_name") or "").strip(), str(chs[0]).lower(),
                   str(c.get("last_status") or ("In Progress" if c.get("active_count") else "")),
                   {"phone_masked": c.get("phone_masked"), "tags": c.get("tags") or [], "last_item": c.get("last_item"), "crm_id": c.get("id")})

    olx_state = _read_json(DATA / "olx_chat_alerts_state.json", {})
    if isinstance(olx_state.get("seen"), dict):
        for name in olx_state["seen"]:
            upsert(str(name), "olx", "OLX")

    styles = _read_json(DATA / "contact_styles.json", {})
    if isinstance(styles, dict):
        for name, style in styles.items():
            upsert(str(name), "tg", "Стиль ответа задан", {"style": style})

    result = list(contacts.values())
    result.sort(key=lambda c: c.get("name") or "")
    for c in result:
        n = c.get("name") or "?"
        letter = n[0].upper()
        c["letter"] = letter if re.match(r"[A-ZА-ЯЁ]", letter) else "#"
    return result


def _build_services() -> list[dict]:
    catalog = [
        ("telegram", "Telegram", "send", "#2AABEE", "Личные диалоги и оператор-бот", "aios-telegram-bot.service", [], "tg"),
        ("olx", "OLX", "storefront", "#002F34", "Чаты, автоответы, коллектор", "aios-olx-autoreply.service", ["aios-olx-collector.service"], "olx"),
        ("instagram", "Instagram", "photo_camera", "#E4405F", "Direct автоответы", "aios-ig-autoreply.service", [], "ig"),
        ("facebook", "Messenger", "chat", "#0084FF", "FB Messenger автоответы", "aios-fb-autoreply.service", [], "messenger"),
        ("viber", "Viber", "call", "#7360F2", "Desktop + phone", "aios-viber-autoreply.service", [], "viber"),
        ("signal", "Signal", "lock", "#3A76F0", "Signal Desktop", "aios-signal-autoreply.service", [], "signal"),
        ("android", "Android Phone", "smartphone", "#3DDC84", "Gateway + Phone Brain", "aios-android-gateway.service", ["aios-phone-brain.service"], "android"),
        ("whatsapp", "WhatsApp", "chat", "#25D366", "Phone / Messages twin", "", [], "whatsapp"),
        ("freelance", "Freelance Brain", "work", "#ff9f0a", "Автономный заработок", "aios-freelance-brain.service", ["aios-autonomous-earnings.service"], "approval"),
        ("converge", "Converge API", "hub", "#3e90ff", "Этот messenger hub", "aios-converge.service", [], "approval"),
    ]
    items, _ = _inbox_items()
    by_ch: dict[str, int] = {}
    for it in items:
        if isinstance(it, dict):
            ch = str(it.get("channel") or "").lower()
            by_ch[ch] = by_ch.get(ch, 0) + 1
    out = []
    for sid, name, icon, color, desc, unit, extras, channel in catalog:
        status = _unit_active(unit) if unit else ("active" if by_ch.get(channel) else "idle")
        connected = status == "active" or (sid == "whatsapp" and by_ch.get("whatsapp", 0) + by_ch.get("wa", 0) > 0)
        detail = ", ".join(f"{u.replace('aios-','').replace('.service','')}:{_unit_active(u)}" for u in extras)
        out.append({
            "id": sid, "name": name, "icon": icon, "color": color, "desc": desc, "channel": channel,
            "status": status, "connected": connected,
            "inbox_count": by_ch.get(channel, 0) + (by_ch.get("tg", 0) if sid == "telegram" else 0),
            "detail": detail,
        })
    return out


def _phone_status() -> dict:
    gw = DATA / "android_gateway"
    bat = _read_json(gw / "battery_alert_state.json", {})
    brain = _read_json(gw / "brain_supervisor.json", {})
    companion = _read_json(gw / "companion.json", {})
    # try metrics exporter style files
    for name in ("phone_status.json", "device_status.json", "status.json"):
        st = _read_json(gw / name, {})
        if st:
            return {"source": name, **st, "brain": brain, "battery_alert": bat}
    return {
        "online": brain.get("fail_streak", 1) == 0 if brain else None,
        "brain": brain,
        "battery_alert": bat,
        "companion": {k: companion.get(k) for k in ("package", "version", "endpoint") if k in companion},
        "gateway_unit": _unit_active("aios-android-gateway.service"),
        "phone_brain_unit": _unit_active("aios-phone-brain.service"),
    }


def _build_settings() -> dict:
    crm = _read_json(DATA / "customer_crm.json", [])
    sales = _read_json(DATA / "sales_lifecycle.json", [])
    finance = _read_json(DATA / "finance.json", [])
    items, updated = _inbox_items()
    approvals = _read_json(DATA / "autonomy_approvals.json", [])
    pending = 0
    if isinstance(approvals, list):
        pending = sum(1 for a in approvals if isinstance(a, dict) and a.get("status") == "pending"
                      and "stress_" not in str((a.get("proposal") or {}).get("chat") or ""))
    unread = sum(1 for it in items if isinstance(it, dict) and it.get("unread"))
    inv = _read_json(DATA / "inventory.json", [])
    return {
        "profile": {"name": "AIOS Operator", "id": "USR-AIOS-01", "role": "Owner / Operator", "theme": "dark"},
        "stats": {
            "inbox_items": len(items), "unread": unread,
            "crm_contacts": len(crm) if isinstance(crm, list) else 0,
            "active_sales": len([s for s in sales if isinstance(s, dict) and s.get("status") not in ("done", "cancelled", "delivered")]) if isinstance(sales, list) else 0,
            "pending_approvals": pending,
            "finance_entries": len(finance) if isinstance(finance, list) else 0,
            "inventory_skus": len(inv) if isinstance(inv, list) else 0,
            "inbox_updated_at": updated,
        },
        "phone": _phone_status(),
        "links": {"crm": "/crm/", "parts": "/parts/", "kernel": "/kernel/", "converge": "/converge/"},
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _normalize_raw_messages(raw: dict, channel: str) -> list[dict]:
    msgs = raw.get("messages") or raw.get("msgs") or raw.get("items") or raw.get("history") or []
    if isinstance(raw.get("dialogs"), list) and not msgs:
        msgs = raw["dialogs"]
    out = []
    if not isinstance(msgs, list):
        return out
    for i, m in enumerate(msgs):
        if not isinstance(m, dict):
            text = str(m)
            out.append({"id": f"m-{i}", "role": "inbound", "text": text, "time": ""})
            continue
        text = str(m.get("text") or m.get("body") or m.get("message") or m.get("content") or m.get("preview") or "")
        if not text:
            continue
        # outbound heuristics
        is_out = bool(m.get("out") or m.get("outgoing") or m.get("from_me") or m.get("is_out")
                      or str(m.get("role") or "").lower() in ("out", "outbound", "me", "operator", "assistant")
                      or str(m.get("sender") or "").lower() in ("me", "operator", "you", "я"))
        role = "outbound" if is_out else "inbound"
        if m.get("system"):
            role = "system"
        out.append({
            "id": str(m.get("id") or f"m-{i}"),
            "role": role,
            "text": text[:2000],
            "time": _fmt_time(str(m.get("time") or m.get("date") or m.get("ts") or m.get("timestamp") or "")),
        })
    return out


def _read_args(channel: str, ref: str, limit: int = 50) -> list[str] | None:
    ch = channel.lower()
    lim = str(limit)
    if ch in ("tg", "telegram"):
        return ["tg", "read", ref, "--limit", lim]
    if ch in ("ig", "instagram"):
        return ["instagram", "dm_read", ref, "--limit", lim]
    if ch in ("messenger", "facebook", "fb"):
        return ["facebook", "messenger_read", ref, "--limit", lim]
    if ch == "viber":
        return ["viber", "read", ref, "--limit", lim]
    if ch == "signal":
        return ["signal", "read", ref, "--limit", lim]
    if ch == "olx":
        return ["olx", "chat", "read", ref, "--limit", lim]
    if ch in ("whatsapp", "wa", "android"):
        return ["messages", "read", ref, "--limit", lim]
    return None


def _thread_cache_get(chat_id: str) -> list[dict] | None:
    cache = _read_json(THREAD_CACHE, {})
    if not isinstance(cache, dict):
        return None
    row = cache.get(chat_id)
    if not isinstance(row, dict):
        return None
    if time.time() - float(row.get("ts") or 0) > 120:
        return None
    msgs = row.get("messages")
    return msgs if isinstance(msgs, list) else None


def _thread_cache_set(chat_id: str, messages: list[dict]) -> None:
    cache = _read_json(THREAD_CACHE, {})
    if not isinstance(cache, dict):
        cache = {}
    cache[chat_id] = {"ts": time.time(), "messages": messages[-100:]}
    # keep last 80 chats
    if len(cache) > 80:
        items = sorted(cache.items(), key=lambda kv: float((kv[1] or {}).get("ts") or 0), reverse=True)[:80]
        cache = dict(items)
    _write_json(THREAD_CACHE, cache)


def _build_send_args(channel: str, ref: str, text: str, confirm: bool) -> list[str]:
    ch = (channel or "").lower()
    flag = ["--confirm"] if confirm else []
    if ch in ("tg", "telegram"):
        return ["tg", "send", ref, text] + flag
    if ch in ("ig", "instagram"):
        return ["instagram", "dm_send", ref, text] + flag
    if ch in ("messenger", "facebook", "fb"):
        return ["facebook", "messenger_send", ref, text] + flag
    if ch == "viber":
        return ["viber", "send", ref, text] + flag
    if ch == "signal":
        return ["signal", "send", ref, text] + flag
    if ch == "olx":
        return ["olx", "chat", "reply", ref, text] + flag
    if ch in ("whatsapp", "wa", "android"):
        return ["messages", "send", ref, text] + flag
    raise HTTPException(status_code=400, detail=f"Отправка в «{channel}» не поддерживается")


def _normalize_send_result(raw: dict, channel: str, ref: str, text: str) -> dict:
    st = str(raw.get("status") or "")
    if st in ("sent", "ok", "published"):
        return {"status": "sent", "channel": channel, "ref": ref, "text": text, "raw_status": st, "message": "Сообщение отправлено"}
    if st in ("need_confirm", "confirm_required"):
        return {"status": "need_confirm", "channel": channel, "ref": ref, "text": text, "raw_status": st, "message": "Требуется подтверждение", "raw": raw}
    err = raw.get("error") or raw.get("message") or st or "unknown error"
    return {"status": "error", "channel": channel, "ref": ref, "text": text, "error": str(err)[:400], "raw_status": st, "raw": raw}


def _store_outbox_message(chat_id: str, channel: str, ref: str, text: str, status: str, meta: dict | None = None) -> dict:
    item = {
        "id": f"out-{int(time.time()*1000)}-{_cid(channel, ref)[:6]}",
        "chat_id": chat_id, "channel": channel, "ref": ref, "role": "outbound",
        "text": text, "status": status,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "time": datetime.now().strftime("%H:%M"), "meta": meta or {},
    }
    box = _load_outbox()
    box.append(item)
    _save_outbox(box)
    return item


def _resolve_chat(chat_id: str) -> dict:
    chat = next((c for c in _build_chats() if c["id"] == chat_id), None)
    if not chat:
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


def _chat_thread(chat_id: str, live: bool = False, limit: int = 50) -> dict:
    chat = _resolve_chat(chat_id)
    messages: list[dict] = []
    source = "local"
    # Авто-подгрузка 50+ сообщений: harvester (каждую минуту) наполняет кэш для всех unread.
    # При открытии чата отдаём кэш мгновенно если он свежий (<120с), даже для unread.
    # Live дергаем только если: пользователь явно нажал ⟳ (live=True) или кэша нет, или кэш протух (>120с для unread, >600с для read)
    cached = _thread_cache_get(chat_id)
    cache_ts = None
    if cached is not None:
        # достаём ts из самого кэша
        raw_cache = _read_json(THREAD_CACHE, {})
        row = raw_cache.get(chat_id) if isinstance(raw_cache, dict) else None
        if isinstance(row, dict):
            try:
                cache_ts = float(row.get("ts") or 0)
            except Exception:
                cache_ts = None
    cache_age = (time.time() - cache_ts) if cache_ts else 9999
    is_unread = bool(chat.get("unread"))
    if live:
        should_fetch_live = True
    elif cached is None:
        should_fetch_live = True
    elif is_unread and cache_age > 120:
        should_fetch_live = True  # unread и кэш старше 2 мин — обновляем
    elif not is_unread and cache_age > 600:
        should_fetch_live = True  # read и кэш старше 10 мин — обновляем фоново
    else:
        should_fetch_live = False

    if True:
        if cached is not None and not should_fetch_live:
            messages = list(cached)
            source = "cache" if not is_unread else "cache_fresh"
        else:
            args = _read_args(str(chat.get("channel") or ""), str(chat.get("ref") or ""), limit=limit)
            if args and chat.get("channel") not in ("approval", "crm", "sale"):
                # live чтение: для новых сообщений без свежего кэша или по явному запросу
                if should_fetch_live or live or cached is None:
                    raw = _run_account_control(args, timeout=150)
                    if raw.get("status") in (None, "ok", "success") or raw.get("messages") or raw.get("msgs"):
                        messages = _normalize_raw_messages(raw, str(chat.get("channel")))
                        source = "live"
                        if messages:
                            _thread_cache_set(chat_id, messages)
                    elif raw.get("status") == "error":
                        # При ошибке live — fallback на кеш если он есть
                        fallback = _thread_cache_get(chat_id)
                        if fallback:
                            messages = list(fallback)
                            source = "cache_fallback"
                        else:
                            messages.append({"id": "read-err", "role": "system",
                                         "text": f"Не удалось прочитать канал: {raw.get('error', '?')[:200]}", "time": ""})
                            source = "error"

    # sales context
    sales = _read_json(DATA / "sales_lifecycle.json", [])
    if isinstance(sales, list):
        for s in sales:
            if not isinstance(s, dict):
                continue
            names = " ".join(str(x) for x in (s.get("chat"), s.get("recipient"), s.get("item")) if x)
            if chat["title"].casefold() in names.casefold() or str(s.get("chat") or "").casefold() == chat["title"].casefold():
                messages.append({
                    "id": f"sale-{s.get('id')}", "role": "system",
                    "text": f"Сделка: {s.get('item')} · {s.get('amount')} · {s.get('status')} · ТТН {s.get('ttn') or '—'}",
                    "time": _fmt_time(str(s.get("updated_at") or "")),
                })

    if chat.get("channel") == "approval":
        approvals = _read_json(DATA / "autonomy_approvals.json", [])
        if isinstance(approvals, list):
            for a in approvals:
                if str(a.get("id")) == str(chat.get("ref") or chat.get("approval_id")):
                    prop = a.get("proposal") or {}
                    params = prop.get("params") or {}
                    text = params.get("text") or a.get("reason") or prop.get("action") or ""
                    messages.append({"id": f"ap-{a.get('id')}", "role": "assistant",
                                     "text": f"[{a.get('verdict')}] {text}", "time": _fmt_time(str(a.get("ts") or ""))})
                    messages.append({"id": f"ap-meta-{a.get('id')}", "role": "system",
                                     "text": f"Платформа: {prop.get('platform')} · чат: {prop.get('chat')} · {a.get('status')}", "time": ""})

    if not messages and chat.get("preview"):
        messages.append({"id": "preview", "role": "inbound", "text": chat["preview"], "time": chat.get("date") or ""})
        messages.append({"id": "hint", "role": "system",
                         "text": "Нажмите ⟳ в чате для live-чтения канала. Outbox Converge подмешивается ниже.", "time": ""})

    for o in _load_outbox():
        if not isinstance(o, dict):
            continue
        if o.get("chat_id") == chat_id or (str(o.get("ref")) == str(chat.get("ref")) and str(o.get("channel")) == str(chat.get("channel"))):
            messages.append({
                "id": o.get("id"), "role": "outbound", "text": o.get("text") or "",
                "time": o.get("time") or _fmt_time(str(o.get("ts") or "")), "status": o.get("status"),
            })

    return {"chat": chat, "messages": messages, "source": source, "can_send": chat.get("channel") not in ("approval", "crm", "sale")}


def _templates() -> list[dict]:
    out = list(DEFAULT_TEMPLATES)
    try:
        r = subprocess.run(
            ["/opt/aios/.venv/bin/python", str(ROOT / "run_followup_templates.py"), "list"],
            capture_output=True, text=True, timeout=10, cwd=str(ROOT),
        )
        data = json.loads(r.stdout or "{}")
        for t in data.get("templates") or []:
            if isinstance(t, dict):
                out.append({
                    "id": f"fu-{t.get('name') or t.get('id') or len(out)}",
                    "title": str(t.get("name") or t.get("title") or "Шаблон")[:40],
                    "text": str(t.get("text") or t.get("body") or ""),
                })
            elif isinstance(t, str):
                out.append({"id": f"fu-{len(out)}", "title": t[:40], "text": t})
    except Exception:
        pass
    # dedupe by text
    seen = set()
    uniq = []
    for t in out:
        key = (t.get("text") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    return uniq


def _system_snapshot() -> dict:
    # host
    host = {}
    try:
        import psutil
        host = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_percent": psutil.disk_usage("/").percent,
            "disk_free_gb": round(psutil.disk_usage("/").free / (1024**3), 2),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds"),
        }
    except Exception as e:
        host = {"error": str(e)}

    units = [
        "aios-converge", "aios-telegram-bot", "aios-olx-autoreply", "aios-olx-collector",
        "aios-fb-autoreply", "aios-ig-autoreply", "aios-viber-autoreply", "aios-signal-autoreply",
        "aios-android-gateway", "aios-phone-brain", "aios-freelance-brain",
        "aios-autonomous-earnings", "aios-dashboard-v3", "docker",
    ]
    services = {u: _unit_active(f"{u}.service" if not u.endswith(".service") and u != "docker" else (u if u.endswith(".service") else f"{u}.service" if u != "docker" else "docker.service")) for u in units}

    items, updated = _inbox_items()
    unread = sum(1 for i in items if isinstance(i, dict) and i.get("unread"))
    approvals = _read_json(DATA / "autonomy_approvals.json", [])
    pending = sum(1 for a in approvals if isinstance(a, dict) and a.get("status") == "pending" and "stress_" not in str((a.get("proposal") or {}).get("chat") or "")) if isinstance(approvals, list) else 0
    sales = _read_json(DATA / "sales_lifecycle.json", [])
    inv = _read_json(DATA / "inventory.json", [])
    finance = _read_json(DATA / "finance.json", [])
    finance_sum = 0.0
    if isinstance(finance, list):
        for f in finance:
            if isinstance(f, dict) and f.get("kind") == "sale":
                try:
                    finance_sum += float(f.get("amount") or 0)
                except Exception:
                    pass

    agents = [
        {"name": "Converge", "status": services.get("aios-converge"), "role": "Messenger hub"},
        {"name": "Telegram Bot", "status": services.get("aios-telegram-bot"), "role": "Operator"},
        {"name": "OLX Autoreply", "status": services.get("aios-olx-autoreply"), "role": "Sales"},
        {"name": "Phone Brain", "status": services.get("aios-phone-brain"), "role": "Android"},
        {"name": "Freelance Brain", "status": services.get("aios-freelance-brain"), "role": "Earnings"},
        {"name": "IG Autoreply", "status": services.get("aios-ig-autoreply"), "role": "Social"},
        {"name": "FB Autoreply", "status": services.get("aios-fb-autoreply"), "role": "Social"},
        {"name": "Viber Autoreply", "status": services.get("aios-viber-autoreply"), "role": "Messaging"},
    ]

    return {
        "host": host,
        "services": services,
        "agents": agents,
        "business": {
            "inbox": len(items), "unread": unread, "inbox_updated_at": updated,
            "pending_approvals": pending,
            "active_sales": len([s for s in sales if isinstance(s, dict) and s.get("status") not in ("done", "cancelled", "delivered")]) if isinstance(sales, list) else 0,
            "inventory_skus": len(inv) if isinstance(inv, list) else 0,
            "sales_sum": finance_sum,
            "profit_rule": "25/25/25/25",
        },
        "phone": _phone_status(),
        "inventory": inv if isinstance(inv, list) else [],
        "sales": sales if isinstance(sales, list) else [],
        "ts": time.time(),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# -------------------- routes --------------------

@app.get("/api/health")
def health():
    items, updated = _inbox_items()
    return {"status": "ok", "app": "converge", "version": "2.0.0", "inbox_items": len(items), "inbox_updated_at": updated, "ts": time.time()}


@app.get("/api/chats")
def api_chats(channel: str | None = None, q: str | None = None, unread_only: bool = Query(False)):
    chats = _build_chats(channel=channel, q=q, unread_only=unread_only)
    _, updated = _inbox_items()
    unread = sum(1 for c in _build_chats() if c.get("unread"))
    return {"updated_at": updated, "count": len(chats), "unread_total": unread, "chats": chats}


@app.get("/api/chats/{chat_id}")
def api_chat_detail(chat_id: str, live: bool = Query(False), limit: int = Query(50, ge=5, le=100)):
    return _chat_thread(chat_id, live=live, limit=limit)


@app.get("/api/chats/{chat_id}/reply-variants")
def api_reply_variants(chat_id: str, limit: int = Query(50, ge=5, le=80), force: bool = Query(False)):
    """Генерация 6 стилей ответа по истории 50+ сообщений (Stitch)."""
    try:
        thread = _chat_thread(chat_id, live=False, limit=limit)
        messages = thread.get("messages") or []
        # Если force или кэш пустой — пробуем live для свежести
        if force and not messages:
            thread = _chat_thread(chat_id, live=True, limit=limit)
            messages = thread.get("messages") or []
        from aios_core.reply_variants import generate_variants, STYLES
        result = generate_variants(chat_id, messages)
        # Добавляем мета чата для фронта
        result["chat"] = thread.get("chat") or {}
        result["messages_count"] = len(messages)
        return result
    except Exception as e:
        from aios_core.reply_variants import _fallback_variants, STYLES
        try:
            chat = _resolve_chat(chat_id)
        except Exception:
            chat = {}
        return {"cid": chat_id, "variants": _fallback_variants(""), "source": f"error:{str(e)[:80]}", "cached": False, "styles": STYLES, "chat": chat, "messages_count": 0}


@app.get("/api/reply-styles")
def api_reply_styles():
    from aios_core.reply_variants import STYLES
    return {"styles": STYLES}


@app.get("/api/contacts")
def api_contacts(channel: str | None = None, q: str | None = None):
    contacts = _build_contacts(channel=channel, q=q)
    return {"count": len(contacts), "contacts": contacts}


@app.get("/api/services")
def api_services():
    services = _build_services()
    return {"count": len(services), "services": services}


@app.get("/api/settings")
def api_settings():
    return _build_settings()


@app.get("/api/templates")
def api_templates():
    t = _templates()
    return {"count": len(t), "templates": t}


@app.get("/api/system")
def api_system():
    return _system_snapshot()


@app.get("/api/business/inventory")
def api_inventory():
    inv = _read_json(DATA / "inventory.json", [])
    return {"count": len(inv) if isinstance(inv, list) else 0, "items": inv if isinstance(inv, list) else []}


@app.get("/api/business/sales")
def api_sales():
    sales = _read_json(DATA / "sales_lifecycle.json", [])
    return {"count": len(sales) if isinstance(sales, list) else 0, "items": sales if isinstance(sales, list) else []}


@app.post("/api/business/ttn/preview")
def api_ttn_preview(payload: dict = Body(...)):
    """Validate TTN payload without creating (dry info)."""
    required = ["detail", "cost", "recipient", "phone", "city", "warehouse"]
    missing = [k for k in required if not str(payload.get(k) or "").strip()]
    if missing:
        raise HTTPException(status_code=400, detail=f"Не хватает полей: {', '.join(missing)}")
    return {
        "status": "ok",
        "preview": {k: payload.get(k) for k in required},
        "message": "Для создания выполните POST /api/business/ttn/create с confirm=true",
        "command_example": f'create "{payload.get("detail")}" {payload.get("cost")} "{payload.get("recipient")}" {payload.get("phone")} "{payload.get("city")}" "{payload.get("warehouse")}"',
    }


@app.post("/api/business/ttn/create")
def api_ttn_create(payload: dict = Body(...)):
    if not payload.get("confirm"):
        return api_ttn_preview(payload) | {"status": "need_confirm"}
    args = [
        "/opt/aios/.venv/bin/python", str(ROOT / "run_ttn.py"), "create",
        str(payload.get("detail")), str(payload.get("cost")),
        str(payload.get("recipient")), str(payload.get("phone")),
        str(payload.get("city")), str(payload.get("warehouse")), "--confirm",
    ]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        out = (r.stdout or "").strip()
        start = out.find("{")
        data = json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-300:] or r.stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return data


@app.post("/api/chats/{chat_id}/send")
def api_chat_send(chat_id: str, payload: dict = Body(...)):
    _purge_pending()
    text_msg = str(payload.get("text") or "").strip()
    confirm = bool(payload.get("confirm"))
    force = bool(payload.get("force"))
    pending_id = str(payload.get("pending_id") or "").strip()
    chat = _resolve_chat(chat_id)
    channel = str(chat.get("channel") or "")
    ref = str(chat.get("ref") or chat.get("title") or "")

    if pending_id:
        pend = PENDING_SENDS.pop(pending_id, None)
        if not pend:
            raise HTTPException(status_code=404, detail="Черновик не найден или истёк (10 мин)")
        text_msg = str(pend.get("text") or text_msg).strip()
        channel = str(pend.get("channel") or channel)
        ref = str(pend.get("ref") or ref)
        chat_id = str(pend.get("chat_id") or chat_id)
        confirm = True

    if not text_msg:
        raise HTTPException(status_code=400, detail="Пустой текст")
    if len(text_msg) > 4000:
        raise HTTPException(status_code=400, detail="Макс. 4000 символов")
    if channel in ("approval", "crm", "sale"):
        raise HTTPException(status_code=400, detail="Системный пункт — выберите чат клиента")

    if not confirm and not force:
        pid = f"p_{_cid(channel, ref)}_{int(time.time())}"
        PENDING_SENDS[pid] = {"id": pid, "ts": time.time(), "chat_id": chat_id, "channel": channel, "ref": ref,
                              "title": chat.get("title"), "text": text_msg}
        draft = _store_outbox_message(chat_id, channel, ref, text_msg, "pending", {"pending_id": pid})
        return {
            "status": "need_confirm", "pending_id": pid, "channel": channel,
            "channel_label": chat.get("channel_label") or channel, "ref": ref, "title": chat.get("title"),
            "text": text_msg, "preview": text_msg[:200], "message": "Проверьте текст и подтвердите",
            "draft": draft, "expires_in": PENDING_TTL_SEC, "chat_id": chat_id,
        }

    args = _build_send_args(channel, ref, text_msg, confirm=True)
    raw = _run_account_control(args, timeout=180)
    result = _normalize_send_result(raw, channel, ref, text_msg)
    out_item = _store_outbox_message(chat_id, channel, ref, text_msg, result["status"],
                                     {"raw_status": result.get("raw_status"), "error": result.get("error")})
    _append_send_log({"ts": datetime.now().isoformat(timespec="seconds"), "chat_id": chat_id, "channel": channel,
                      "ref": ref, "status": result["status"], "text": text_msg[:500]})
    result["outbox"] = out_item
    result["title"] = chat.get("title")
    result["channel_label"] = chat.get("channel_label") or channel
    result["chat_id"] = chat_id
    if result["status"] == "error":
        return JSONResponse(result, status_code=502)
    # invalidate thread cache
    cache = _read_json(THREAD_CACHE, {})
    if isinstance(cache, dict) and chat_id in cache:
        cache.pop(chat_id, None)
        _write_json(THREAD_CACHE, cache)
    return result


@app.post("/api/chats/{chat_id}/send/retry")
def api_chat_send_retry(chat_id: str, payload: dict = Body(...)):
    """Retry last failed outbox message or provided text."""
    text_msg = str(payload.get("text") or "").strip()
    outbox_id = str(payload.get("outbox_id") or "").strip()
    if not text_msg and outbox_id:
        for o in reversed(_load_outbox()):
            if o.get("id") == outbox_id:
                text_msg = str(o.get("text") or "")
                break
    if not text_msg:
        # last error for chat
        for o in reversed(_load_outbox()):
            if o.get("chat_id") == chat_id and o.get("status") == "error":
                text_msg = str(o.get("text") or "")
                break
    if not text_msg:
        raise HTTPException(status_code=400, detail="Нечего повторять")
    return api_chat_send(chat_id, {"text": text_msg, "confirm": True, "force": True})


@app.post("/api/chats/{chat_id}/send/cancel")
def api_chat_send_cancel(chat_id: str, payload: dict = Body(default={})):
    _purge_pending()
    pending_id = str((payload or {}).get("pending_id") or "").strip()
    if pending_id and pending_id in PENDING_SENDS:
        PENDING_SENDS.pop(pending_id, None)
        return {"status": "cancelled", "pending_id": pending_id}
    killed = [k for k, v in list(PENDING_SENDS.items()) if v.get("chat_id") == chat_id]
    for k in killed:
        PENDING_SENDS.pop(k, None)
    return {"status": "cancelled", "pending_ids": killed}


@app.get("/api/outbox")
def api_outbox(limit: int = 50):
    items = list(reversed(_load_outbox()))[: max(1, min(limit, 200))]
    return {"count": len(items), "items": items}


@app.post("/api/refresh")
def api_refresh():
    collector = ROOT / "run_inbox_collector.py"
    if not collector.exists():
        return {"status": "skipped", "reason": "collector missing"}
    try:
        subprocess.Popen(["/opt/aios/.venv/bin/python", str(collector)], cwd=str(ROOT),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return {"status": "started", "message": "Обновление инбокса запущено"}
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/kernel")
@app.get("/kernel/")



def kernel_index():
    index = KERNEL_STATIC / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="kernel UI missing")
    return FileResponse(index)


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
if KERNEL_STATIC.exists():
    app.mount("/kernel_static", StaticFiles(directory=str(KERNEL_STATIC)), name="kernel_static")


def main():
    import uvicorn
    host = os.environ.get("CONVERGE_HOST", "127.0.0.1")
    port = int(os.environ.get("CONVERGE_PORT", "8092"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
