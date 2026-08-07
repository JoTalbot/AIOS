"""Генерация 10 стилей ответа на основе истории диалога (Stitch-дизайн) — 10 вариантов.

Использует LLMBalancer для генерации вариантов в стилях:
деловой, дружеский, сарказм, романтичный, кратко, раздраженно, официальный, юмор, эмпатия, вдохновляющий.
Кэширует на 5 минут по cid.
"""
from __future__ import annotations
import json
import time
import hashlib
from pathlib import Path
from typing import Any

ROOT = Path('/root/AIOS')
CACHE_PATH = ROOT / 'data' / 'reply_variants_cache.json'
CACHE_TTL_SEC = 300

STYLES = [
    {"id": "delovoy", "label": "ДЕЛОВОЙ", "icon": "work", "color": "#0058bc", "hint": "Принято в работу. Ожидайте обновление."},
    {"id": "druzheskiy", "label": "ДРУЖЕСКИЙ", "icon": "celebration", "color": "#006c46", "hint": "Звучит как отличный план! Давай..."},
    {"id": "sarkazm", "label": "САРКАЗМ", "icon": "sentiment_very_satisfied", "color": "#7c4d00", "hint": "О, еще одна задача в спринт? Моя любимая..."},
    {"id": "romantichniy", "label": "РОМАНТИЧНЫЙ", "icon": "favorite", "color": "#ba1a1a", "hint": "Твои идеи сияют ярче, чем этот..."},
    {"id": "kratko", "label": "КРАТКО", "icon": "bolt", "color": "#0058bc", "hint": "Ок, сделаю."},
    {"id": "razdrazhenno", "label": "РАЗДРАЖЕННО", "icon": "mood_bad", "color": "#93000a", "hint": "Я же уже говорил, что займусь этим..."},
    {"id": "oficialniy", "label": "ОФИЦИАЛЬНЫЙ", "icon": "gavel", "color": "#4057a5", "hint": "Уважаемый клиент, подтверждаю..."},
    {"id": "yumor", "label": "ЮМОР", "icon": "comedy_mask", "color": "#a53d00", "hint": "Ха, ну вы даёте! 😄"},
    {"id": "empatiya", "label": "ЭМПАТИЯ", "icon": "volunteer_activism", "color": "#2e5c00", "hint": "Понимаю, как это важно..."},
    {"id": "vdokhnovlyayushchiy", "label": "ВДОХНОВЛЯЮЩИЙ", "icon": "rocket_launch", "color": "#004493", "hint": "Отличный выбор! Вместе сделаем..."},
]

SYSTEM_PROMPT = """Ты — AI-помощник менеджера по продажам автозапчастей в AIOS Converge.
Твоя задача — на основе истории диалога с клиентом сгенерировать 10 вариантов ответа на ПОСЛЕДНЕЕ входящее сообщение клиента.

Стили (отвечай строго в JSON с ключами):
- delovoy: деловой, формальный, вежливый. Пример: "Принято в работу. Ожидайте обновление по заказу в течение часа."
- druzheskiy: дружелюбный, неформальный, с энтузиазмом. Пример: "Звучит как отличный план! Давай сделаем еще лучше."
- sarkazm: саркастичный, ироничный, но без грубости. Пример: "О, еще одна задача в спринт? Моя любимая часть дня."
- romantichniy: романтичный, теплый, эмоциональный. Пример: "Твои идеи сияют ярче, чем этот интерфейс."
- kratko: максимально коротко, 1-2 предложения. Пример: "Ок, сделаю."
- razdrazhenno: раздраженный, уставший, но без оскорблений. Пример: "Я же уже говорил, что займусь этим, когда закончу."
- oficialniy: официальный, уважительный, с обращением. Пример: "Уважаемый клиент, подтверждаю получение запроса. Подготовлю ответ в течение часа."
- yumor: юмористический, лёгкий, с шуткой. Пример: "Ха, ну вы даёте! Такая фара точно не даст заскучать на дороге 😄"
- empatiya: эмпатичный, поддерживающий, понимающий. Пример: "Понимаю, как важно быстро решить вопрос с деталью. Помогу всем, чем смогу."
- vdokhnovlyayushchiy: вдохновляющий, мотивирующий. Пример: "Отличный выбор! Вместе сделаем ваш авто ещё лучше — погнали!"

Правила:
- Учитывай контекст истории (последние 50 сообщений) и последнее сообщение клиента
- Каждый вариант — 1-3 предложения, естественный, готов к отправке
- Язык ответа — как у клиента (ru/uk), если клиент на украинском — отвечай на украинском
- Не добавляй префиксы "Вариант:", только сам текст
- Верни ТОЛЬКО валидный JSON без markdown, без пояснений
Пример вывода:
{"delovoy":"...","druzheskiy":"...","sarkazm":"...","romantichniy":"...","kratko":"...","razdrazhenno":"...","oficialniy":"...","yumor":"...","empatiya":"...","vdokhnovlyayushchiy":"..."}
"""


def _cache_key(cid: str, history_hash: str) -> str:
    return f"{cid}:{history_hash}"

def _history_hash(messages: list[dict]) -> str:
    raw = "|".join(f"{m.get('role')}:{m.get('text','')[:80]}" for m in messages[-10:])
    return hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()[:12]

def _read_cache() -> dict:
    try:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}

def _write_cache(data: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

def _fallback_variants(last_text: str) -> dict[str, str]:
    base = (last_text or "ваше сообщение").strip()[:60]
    return {
        "delovoy": f'Принято в работу. По "{base}" подготовлю информацию и вернусь с ответом в ближайшее время.',
        "druzheskiy": f'Звучит как отличный план! По "{base}" — давай сделаем всё чётко, подскажу детали.',
        "sarkazm": f'О, еще одна задача в спринт? По "{base}" — моя любимая часть дня, конечно гляну.',
        "romantichniy": f'Твои идеи сияют ярче интерфейса. По "{base}" — сделаю с душой.',
        "kratko": "Ок, сделаю.",
        "razdrazhenno": "Я же уже говорил, что займусь этим — сейчас закрою текущее и вернусь.",
        "oficialniy": f'Уважаемый клиент, подтверждаю запрос по "{base}". Подготовлю детальный ответ в течение часа.',
        "yumor": f'Ха, по "{base}" — вы точно знаете, как поднять настроение! Гляну с улыбкой 😄',
        "empatiya": f'Понимаю, насколько важен вопрос по "{base}". Сделаю всё, чтобы помочь максимально быстро.',
        "vdokhnovlyayushchiy": f'Отличный выбор по "{base}"! Вместе сделаем ваш авто ещё лучше — погнали к результату!',
    }

def generate_variants(cid: str, messages: list[dict]) -> dict[str, Any]:
    if not messages:
        return {"cid": cid, "variants": _fallback_variants(""), "source": "fallback_empty", "cached": False}
    history = messages[-50:]
    lines = []
    for m in history[-20:]:
        role = m.get('role','inbound')
        prefix = "Клиент:" if role == 'inbound' else "Менеджер:"
        txt = str(m.get('text','')).strip()[:300]
        if txt:
            lines.append(f"{prefix} {txt}")
    last_inbound = next((m for m in reversed(history) if m.get('role')=='inbound'), history[-1] if history else {"text":""})
    last_text = str(last_inbound.get('text','')).strip()[:500]
    if not last_text:
        last_text = str(history[-1].get('text',''))[:500] if history else ""

    hhash = _history_hash(history)
    cache = _read_cache()
    key = _cache_key(cid, hhash)
    now = time.time()
    if key in cache:
        entry = cache[key]
        if now - float(entry.get('ts',0)) < CACHE_TTL_SEC:
            return {"cid": cid, "variants": entry.get('variants', {}), "source": "cache", "cached": True, "styles": STYLES}

    try:
        from aios_core.llm_balancer import LLMBalancer
        balancer = LLMBalancer()
        prompt = "История диалога (последние сообщения сверху вниз):\n" + "\n".join(lines[-20:]) + f"\n\nПоследнее сообщение клиента для ответа: \"{last_text}\"\n\nСгенерируй 10 вариантов ответа в JSON."
        raw = balancer.chat(
            [{"role":"user","content": prompt}],
            system=SYSTEM_PROMPT,
            max_tokens=1200,
            temperature=0.7,
            task_type="chat"
        )
        text = str(raw or "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >=0 and end>start:
            text = text[start:end+1]
        data = json.loads(text)
        variants = {}
        for s in STYLES:
            sid = s["id"]
            val = str(data.get(sid) or data.get(sid.upper()) or "").strip()[:500]
            if not val:
                val = _fallback_variants(last_text)[sid]
            variants[sid] = val
        cache[key] = {"ts": now, "variants": variants, "last_text": last_text[:120]}
        if len(cache) > 100:
            sorted_items = sorted(cache.items(), key=lambda kv: float(kv[1].get('ts',0)), reverse=True)[:80]
            cache = dict(sorted_items)
        _write_cache(cache)
        return {"cid": cid, "variants": variants, "source": "llm", "cached": False, "styles": STYLES, "llm_raw_len": len(str(raw))}
    except Exception as e:
        variants = _fallback_variants(last_text)
        return {"cid": cid, "variants": variants, "source": f"fallback_error:{str(e)[:80]}", "cached": False, "styles": STYLES}
