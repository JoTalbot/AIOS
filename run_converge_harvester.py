#!/usr/bin/env python3
"""AIOS Converge Harvester — автоподгрузка 50+ сообщений при новом входящем.

Запускается каждые 60с (systemd timer) или по событию.
Логика:
  1) Читает inbox_cache.json (общий инбокс) и android_gateway/notifications.json (пуш-уведомления телефона)
  2) Находит непрочитанные чаты (unread=true) где ещё не делали harvest за последние 10 минут
  3) Для каждого такого чата вызывает run_account_control.py <channel> read <ref> --limit 50
  4) Результат сохраняет в data/converge_thread_cache.json (для мгновенного показа в Converge)
     и в data/threads/<cid>.json (персистентно 80 последних, для истории)
  5) Также обновляет data/inbox_cache.json preview если там было коротко обрезано

Поддерживает: tg, viber, signal, ig/instagram, messenger/facebook, olx, whatsapp/ime/android
Не требует подтверждения, только чтение.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/root/AIOS")
DATA = ROOT / "data"
THREAD_CACHE = DATA / "converge_thread_cache.json"
INBOX_CACHE = DATA / "inbox_cache.json"
NOTIF_JSON = DATA / "android_gateway" / "notifications.json"
HARVESTER_STATE = DATA / "converge_harvester_state.json"
THREADS_DIR = DATA / "threads"

# сколько чатов обрабатывать за один цикл (чтобы не вешать систему OCR)
MAX_CHATS_PER_RUN = 3
# не трогать один и тот же чат чаще чем раз в N секунд (даже если он unread)
HARVEST_COOLDOWN_SEC = 600
LIMIT = 50

def _read_json(path: Path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _cid(channel: str, ref: str) -> str:
    return hashlib.sha1(f"{channel}|{ref}".encode("utf-8", errors="ignore")).hexdigest()[:16]

def _run_account_control(args: list[str], timeout: int = 150) -> dict:
    py = "/opt/aios/.venv/bin/python"
    helper = str(ROOT / "run_account_control.py")
    # Viber/Signal требуют Xvfb
    needs_x = not (len(args) >= 2 and args[0]=="google" and args[1] in ("gmail_list","gmail_send","gmail_search","open"))
    # telegram/viber/signal/google etc handled, but always check if needs X is true for viber/signal
    if args and args[0] in ("viber","signal"):
        needs_x = False  # viber_control already handles DISPLAY :1 without xvfb-run, converge app uses direct call without xvfb
        # Actually viber_control uses DISPLAY=:1 directly, not xvfb-run, so we don't wrap
        cmd = [py, helper] + args
    elif needs_x and args[0] not in ("tg",):
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, helper] + args
    else:
        cmd = [py, helper] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"status":"error", "error":"timeout"}
    out = (r.stdout or "").strip()
    if not out:
        return {"status":"error", "error": (r.stderr or "empty")[-400:]}
    try:
        start = out.find("{")
        return json.loads(out[start:]) if start>=0 else {"status":"error", "error": out[-400:]}
    except Exception:
        return {"status":"error", "error": out[-400:]}

def _build_read_args(channel: str, ref: str, limit: int = 50):
    ch = channel.lower()
    lim = str(limit)
    if ch in ("tg","telegram"):
        return ["tg","read",ref,"--limit",lim]
    if ch in ("ig","instagram"):
        return ["instagram","dm_read",ref,"--limit",lim]
    if ch in ("messenger","facebook","fb"):
        return ["facebook","messenger_read",ref,"--limit",lim]
    if ch == "viber":
        return ["viber","read",ref,"--limit",lim]
    if ch == "signal":
        return ["signal","read",ref,"--limit",lim]
    if ch == "olx":
        return ["olx","chat","read",ref,"--limit",lim]
    if ch in ("whatsapp","wa","android","ime"):
        return ["messages","read",ref,"--limit",lim]
    return None

def _thread_cache_get(chat_id: str):
    cache = _read_json(THREAD_CACHE, {})
    if not isinstance(cache, dict):
        return None
    row = cache.get(chat_id)
    if not isinstance(row, dict):
        return None
    if time.time() - float(row.get("ts") or 0) > 600:
        return None
    return row.get("messages")

def _thread_cache_set(chat_id: str, messages: list[dict]):
    cache = _read_json(THREAD_CACHE, {})
    if not isinstance(cache, dict):
        cache = {}
    cache[chat_id] = {"ts": time.time(), "messages": messages[-100:]}
    if len(cache) > 80:
        items = sorted(cache.items(), key=lambda kv: float((kv[1] or {}).get("ts") or 0), reverse=True)[:80]
        cache = dict(items)
    _write_json(THREAD_CACHE, cache)

def _persist_thread(channel: str, ref: str, messages: list[dict]):
    cid = _cid(channel, ref)
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    path = THREADS_DIR / f"{cid}.json"
    existing = _read_json(path, [])
    if not isinstance(existing, list):
        existing = []
    seen = {str(m.get("text") or "").strip() for m in existing}
    for m in messages:
        txt = str(m.get("text") or "").strip()
        if txt and txt not in seen:
            existing.append(m)
            seen.add(txt)
    existing = existing[-80:]
    _write_json(path, existing)
    try:
        idx_path = DATA / "threads_index.json"
        idx = _read_json(idx_path, {})
        if not isinstance(idx, dict):
            idx = {}
        preview = ""
        if messages:
            last = messages[-1] if isinstance(messages[-1], dict) else {}
            preview = str(last.get("text") or "")[:160]
        title = ref
        import datetime
        idx[cid] = {"channel": channel, "ref": ref, "title": title, "preview": preview, "updated_at": datetime.datetime.now().isoformat(timespec="seconds"), "messages_count": len(existing)}
        arch_path = DATA / "inbox_archive.json"
        arch = _read_json(arch_path, [])
        if not isinstance(arch, list):
            arch = []
        import hashlib
        existing_cids = set()
        for a in arch:
            if isinstance(a, dict):
                ch2 = str(a.get("channel") or "").lower()
                ref2 = str(a.get("ref") or "")
                existing_cids.add(hashlib.sha1(f"{ch2}|{ref2}".encode()).hexdigest()[:16])
        if cid not in existing_cids:
            arch.append({"channel": channel, "ref": ref, "title": title, "preview": preview, "unread": False, "date": ""})
            arch = arch[-500:]
            _write_json(arch_path, arch)
        _write_json(idx_path, idx)
    except Exception:
        pass
    # Pre-warm reply variants cache for instant UI (Stitch)
    try:
        from aios_core.reply_variants import generate_variants
        generate_variants(cid, messages)
    except Exception:
        pass
    return path

def _normalize(raw: dict):
    msgs = raw.get("messages") or raw.get("msgs") or raw.get("items") or raw.get("history") or []
    if isinstance(raw.get("dialogs"), list) and not msgs:
        msgs = raw["dialogs"]
    out = []
    if not isinstance(msgs, list):
        return out
    for i,m in enumerate(msgs):
        if not isinstance(m, dict):
            txt = str(m)
            out.append({"id":f"m-{i}","role":"inbound","text":txt,"time":""})
            continue
        txt = str(m.get("text") or m.get("body") or m.get("message") or m.get("content") or m.get("preview") or "")[:2000]
        if not txt:
            continue
        is_out = bool(m.get("out") or m.get("outgoing") or m.get("from_me") or m.get("is_out") or str(m.get("role") or "").lower() in ("out","outbound","me") )
        role = "outbound" if is_out else "inbound"
        if m.get("mine") and not is_out:
            # viber/signal mine heauristic
            if bool(m.get("mine")):
                role = "outbound"
        out.append({"id":str(m.get("id") or f"m-{i}"),"role":role,"text":txt,"time":str(m.get("time") or m.get("date") or "")[:16]})
    return out

def main() -> int:
    inbox = _read_json(INBOX_CACHE, {})
    items = inbox.get("items") if isinstance(inbox, dict) else []
    if not isinstance(items, list):
        items = []
    # also collect from notifications that are unread and correspond to messenger
    notif_items = _read_json(NOTIF_JSON, [])
    if isinstance(notif_items, list):
        for ev in notif_items[-20:]:
            if not isinstance(ev, dict):
                continue
            if ev.get("read"):
                continue
            app = str(ev.get("app") or "")
            title = str(ev.get("title") or "").strip()
            text = str(ev.get("text") or "")
            if not title or "AIOS" in title or "выгодный" in text.lower():
                continue
            # Map app to channel
            ch = None
            if app == "Viber": ch = "viber"
            elif app in ("WhatsApp","com.whatsapp"): ch = "whatsapp"
            elif "iMe" in app: ch = "ime"
            elif "Telegram" in app: ch = "tg"
            else: ch = "android"
            # avoid duplicates already in inbox
            already = any(str(it.get("ref") or "").lower()==title.lower() and str(it.get("channel") or "").lower()==ch for it in items if isinstance(it, dict))
            if already:
                continue
            items.append({"channel":ch, "ref":title, "title":title, "preview":text[:120], "unread":True})

    state = _read_json(HARVESTER_STATE, {})
    if not isinstance(state, dict):
        state = {}
    last_harvest = state.get("last") if isinstance(state.get("last"), dict) else {}
    
    # Выбираем кандидатов: unread=true, не в cooldown
    candidates = []
    now = time.time()
    for it in items:
        if not isinstance(it, dict): continue
        if not it.get("unread"): continue
        ch = str(it.get("channel") or "").lower()
        ref = str(it.get("ref") or it.get("title") or "").strip()
        if not ch or not ref: continue
        if ch in ("approval","crm","sale"): continue
        # check cooldown
        cid = _cid(ch, ref)
        last_ts = float(last_harvest.get(cid, 0) or 0)
        if now - last_ts < HARVEST_COOLDOWN_SEC:
            continue
        candidates.append((ch, ref, it))
    # Приоритет: быстрые API (tg, ig, messenger, olx) перед медленными OCR (viber, signal)
    priority = {"tg":0, "telegram":0, "ig":1, "instagram":1, "messenger":1, "facebook":1, "fb":1, "olx":1, "whatsapp":2, "wa":2, "ime":2, "android":2, "viber":3, "signal":3}
    candidates = sorted(candidates, key=lambda x: priority.get(x[0].lower(), 9))
    candidates = candidates[:MAX_CHATS_PER_RUN]
    if not candidates:
        print(json.dumps({"status":"ok","harvested":0,"reason":"no new unread"}, ensure_ascii=False))
        return 0

    harvested = 0
    errors = []
    for ch, ref, meta in candidates:
        cid = _cid(ch, ref)
        args = _build_read_args(ch, ref, limit=LIMIT)
        if not args:
            errors.append(f"{ch}/{ref}: no args")
            continue
        print(f"[harvester] {ch}/{ref} -> {args} ...", flush=True)
        raw = _run_account_control(args, timeout=150)
        if raw.get("status") == "error" and not raw.get("messages"):
            errors.append(f"{ch}/{ref}: {raw.get('error','err')[:80]}")
            # даже при ошибке ставим cooldown чтобы не спамить OCR каждую минуту
            last_harvest[cid] = now
            continue
        msgs = _normalize(raw)
        if not msgs:
            # fallback: хотя бы preview
            preview = str(meta.get("preview") or "")
            if preview:
                msgs = [{"id":"preview","role":"inbound","text":preview,"time":""}]
            else:
                errors.append(f"{ch}/{ref}: empty")
                continue
        # Сохраняем в thread cache для converge
        _thread_cache_set(cid, msgs)
        _persist_thread(ch, ref, msgs)
        # Pre-warm reply variants cache for instant UI (Stitch)
        try:
            from aios_core.reply_variants import generate_variants
            generate_variants(cid, msgs)
        except Exception:
            pass
        last_harvest[cid] = now
        harvested += 1
        print(f"[harvester] {ch}/{ref} ok: {len(msgs)} msgs (scrolls={raw.get('scrolls','n/a')})", flush=True)
        # Пауза между OCR-чатами чтобы не пересекаться по UI lock
        time.sleep(2)

    state["last"] = last_harvest
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    state["last_run"] = {"harvested": harvested, "errors": errors}
    _write_json(HARVESTER_STATE, state)
    print(json.dumps({"status":"ok","harvested":harvested,"errors":errors}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
