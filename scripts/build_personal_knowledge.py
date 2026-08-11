#!/usr/bin/env python3
"""
AIOS - Построение "личной базы знаний" для RAG: чаты + профиль пользователя.

Собирает переписки (Viber/Telegram/inbox) и данные профиля владельца в
дополнительные чанки корпуса data/rag/corpus_personal.jsonl с типами
"chats" и "user_profile". Затем объединяет с основным корпусом.

Запуск:
    python scripts/build_personal_knowledge.py
"""
from __future__ import annotations

import os
import json
import argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path("/root/AIOS")
DATA = REPO_ROOT / "data"
OUT = DATA / "rag" / "corpus_personal.jsonl"

LOG_TAG = "[PersonalKnowledge]"


def _chunk(text: str, doc_id: str, meta: dict, chunk_chars: int = 3000, overlap: int = 400):
    text = text.strip()
    chunks = []
    if not text:
        return chunks
    for i in range(0, len(text), chunk_chars - overlap):
        piece = text[i:i + chunk_chars].strip()
        if piece:
            chunks.append({"id": f"{doc_id}#{i // (chunk_chars - overlap)}",
                           "text": piece, "metadata": dict(meta, offset=i)})
    return chunks


def _safe_load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def _useful(text: str, min_len: int = 4) -> bool:
    """Отсеивает мусорные превью (слишком короткие / бессмысленные)."""
    t = (text or "").strip()
    if len(t) < min_len:
        return False
    # отсеять явный мусор: фото, share-ссылки без текста, одинарные символы
    low = t.lower()
    junk_markers = ["photo message", "@photo", "share/1", "share/", "attachment",
                    "you_ notification", "this message", "сообщение недоступно"]
    if any(j in low for j in junk_markers):
        return False
    # надо чтобы было достаточно букв (кириллица/латиница)
    letters = sum(ch.isalpha() for ch in t)
    return letters >= 6


def _collect_chats() -> list[dict]:
    """Собирает переписки из inbox/outbox/logs."""
    chunks = []

    # 1) inbox_archive.json (входящие)
    p = DATA / "inbox_archive.json"
    d = _safe_load(p)
    n_useful = 0
    if isinstance(d, list):
        for i, m in enumerate(d):
            if not isinstance(m, dict):
                continue
            ch = m.get("channel", "?")
            ref = m.get("ref", "") or m.get("title", "")
            preview = m.get("preview", "") or ""
            if _useful(preview):
                text = f"[Входящее сообщение][{ch}] от: {ref}\n{preview}"
                chunks += _chunk(text, f"inbox_archive#{i}",
                                 {"type": "chats", "source": "inbox_archive", "channel": ch, "contact": ref})
                n_useful += 1
        print(f"{LOG_TAG} inbox_archive: {n_useful} полезных")

    # 2) inbox_cache.json (входящие)
    p = DATA / "inbox_cache.json"
    d = _safe_load(p)
    n_cache = 0
    if isinstance(d, dict) and isinstance(d.get("items"), list):
        for i, m in enumerate(d["items"]):
            if not isinstance(m, dict):
                continue
            ref = m.get("ref", "") or m.get("title", "")
            preview = m.get("preview", "") or ""
            if _useful(preview):
                text = f"[Входящее][{m.get('channel','?')}] от: {ref}\n{preview}"
                chunks += _chunk(text, f"inbox_cache#{i}",
                                 {"type": "chats", "source": "inbox_cache", "channel": m.get("channel"), "contact": ref})
                n_cache += 1
        print(f"{LOG_TAG} inbox_cache: {n_cache} полезных")

    # 3) converge_outbox.json (исходящие)
    p = DATA / "converge_outbox.json"
    d = _safe_load(p)
    msgs = []
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, list):
                msgs += v
    elif isinstance(d, list):
        msgs = d
    out_count = 0
    for i, m in enumerate(msgs):
        if not isinstance(m, dict):
            continue
        text = m.get("text", "").strip()
        if not text:
            continue
        ref = m.get("ref", "") or m.get("chat_id", "")
        ch = m.get("channel", "?")
        ts = m.get("ts", "") or m.get("time", "")
        line = f"[Отправлено][{ch}] в чат: {ref} ({ts})\n{text}"
        chunks += _chunk(line, f"outbox#{i}", {"type": "chats", "source": "converge_outbox", "channel": ch, "contact": ref})
        out_count += 1
    print(f"{LOG_TAG} converge_outbox: +{out_count} сообщений")

    # 4) converge_send_log.jsonl (отправка)
    p = DATA / "converge_send_log.jsonl"
    if p.exists():
        n = 0
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines()):
            try:
                m = json.loads(line)
            except Exception:
                continue
            text = m.get("text", "").strip()
            if not text:
                continue
            ref = m.get("ref", "") or m.get("chat_id", "")
            line_txt = f"[Отправлено][{m.get('channel','?')}] в чат: {ref}\n{text}"
            chunks += _chunk(line_txt, f"sendlog#{i}", {"type": "chats", "source": "converge_send_log", "contact": ref})
            n += 1
        print(f"{LOG_TAG} converge_send_log: +{n} сообщений")

    return chunks


def _collect_profile() -> list[dict]:
    """Собирает профиль владельца из данных проекта."""
    chunks = []
    profile = {}

    # базовые данные владельца AIOS
    profile["owner"] = {
        "name": "Jo Talbot",
        "emails": ["jo.talbot@gmail.com", "dedsinfo@gmail.com"],
        "phones": ["+380959052288"],
        "location": "Кропивницкий, Украина",
        "kaggle": "jotalbot",
        "github": "JoTalbot/AIOS",
        "role": "Владелец AIOS (AI Operating System)",
    }

    # платформы/мессенджеры, которыми пользуется владелец
    profile["messengers"] = {
        "viber": True, "telegram": True, "signal": True, "whatsapp": True,
        "facebook_messenger": True, "instagram_dm": True, "google_messages": True,
        "olx": True,
    }

    # бизнес-активность владельца (из проектов AIOS)
    profile["business_activity"] = {
        "freelance": "Freelancehunt, Upwork, Fiverr (автономный фриланс-бrain)",
        "quant_trading": "крипто-трейдинг (BTC, ETH, SOL, 24 актива)",
        "ecommerce": "OLX-продажи (авторазборка, запчасти, автомобили)",
        "ai_automation": "AIOS - самообучающаяся система автоматизации",
    }

    # голосовые профили
    p = DATA / "voice_profiles_db.json"
    d = _safe_load(p)
    if d:
        profile["voice_profiles"] = str(d)[:1500]

    # из inbox_archive определить контакты (по частоте)
    from collections import Counter
    p = DATA / "inbox_archive.json"
    d = _safe_load(p)
    contacts = Counter()
    if isinstance(d, list):
        for m in d:
            if isinstance(m, dict) and m.get("ref"):
                contacts[m["ref"]] += 1
    profile["top_contacts"] = {ref: n for ref, n in contacts.most_common(20)}

    # из inbox_cache
    p = DATA / "inbox_cache.json"
    d = _safe_load(p)
    inbox_contacts = []
    if isinstance(d, dict) and isinstance(d.get("items"), list):
        for m in d["items"]:
            if isinstance(m, dict) and m.get("ref") and m.get("preview"):
                inbox_contacts.append({"contact": m["ref"], "channel": m.get("channel"),
                                       "last": m.get("preview", "")[:80]})
    profile["recent_inbox"] = inbox_contacts[:20]

    # активность
    profile["chat_activity"] = {
        "inbox_messages_total": len(_safe_load(DATA / "inbox_archive.json") or []),
        "recent_inbox_count": len(inbox_contacts),
    }

    text = json.dumps(profile, ensure_ascii=False, indent=1)
    chunks += _chunk(text, "user_profile#0", {"type": "user_profile", "source": "owner_profile"})

    # Дополнительные "заметные" чанки профиля, чтобы ключевые факты находились надёжно
    owner = profile["owner"]
    facts = [
        "ПРОФИЛЬ ВЛАДЕЛЬЦА AIOS: Владельца AIOS зовут Jo Talbot (Джо Талбот).",
        f"EMAIL владельца AIOS: {', '.join(owner['emails'])}.",
        f"ТЕЛЕФОН владельца AIOS: {', '.join(owner['phones'])}.",
        f"Владелец AIOS находится в {owner['location']}.",
        "Владелец AIOS использует мессенджеры: Viber, Telegram, Signal, WhatsApp, Facebook Messenger, Instagram DM, Google Messages, OLX.",
        "Владелец AIOS занимается фрилансом (Freelancehunt, Upwork, Fiverr), крипто-трейдингом и продажами на OLX (авторазборка, запчасти, автомобили).",
    ]
    for idx, f in enumerate(facts, start=1):
        chunks += _chunk(f, f"user_profile#fact{idx}",
                         {"type": "user_profile", "source": "owner_profile", "fact": True})
    print(f"{LOG_TAG} профиль владельца: {len(chunks)} чанк(а) (включая ключевые факты)")
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true", help="объединить с основным корпусом")
    args = ap.parse_args()

    all_chunks = _collect_chats() + _collect_profile()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    print(f"{LOG_TAG} Всего личных чанков: {len(all_chunks)} -> {OUT}")

    if args.merge:
        main_corpus = DATA / "rag" / "corpus.jsonl"
        merged = DATA / "rag" / "corpus_full.jsonl"
        with open(main_corpus, encoding="utf-8") as f1, open(OUT, encoding="utf-8") as f2, open(merged, "w", encoding="utf-8") as fo:
            fo.write(f1.read())
            fo.write(f2.read())
        print(f"{LOG_TAG} Объединённый корпус: {merged}")


if __name__ == "__main__":
    main()
