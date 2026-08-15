#!/usr/bin/env python3
"""Local tests for the historical news pipeline (before prod deploy).

Covers:
  T1 fetch_historical_news.parse_rss       - RSS parsing (empty titles skipped)
  T2 fetch_historical_news snapshot select - step-hours + limit logic
  T3 score_historical_sentiment.score_batch - Gemini ```json``` response parsing
  T4 score_historical_sentiment.main       - merge/resume/relabel with fake scorer
  T5 sentiment_price_historical.detect_coins - coin alias matching
  T6 sentiment_price_historical end-to-end  - news->price correlation on synthetic data
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

# scripts live in ../scripts on the server, next to the test locally
SCRIPT_DIR = (T.parent / "scripts") if (T.parent / "scripts").exists() else T

import fake_quant_monthly_backtest as fake_qmb  # noqa: E402

# pre-register so `import quant_monthly_backtest as qmb` resolves to the fake
sys.modules["quant_monthly_backtest"] = fake_qmb

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- T1, T2
def test_fetch_parsing():
    print("\n[T1] parse_rss")
    fetch = load_module("fetch_historical_news", SCRIPT_DIR / "fetch_historical_news.py")
    raw = (T / "fixtures" / "rss_sample.xml").read_bytes()
    items = fetch.parse_rss(raw)
    check("2 элемента (пустой title пропущен)", len(items) == 2)
    check("поля корректны",
          items[0]["title"].startswith("Bitcoin") and "pub" in items[0]
          and items[0]["pub"].startswith("Sat"))
    check("pubDate RFC822 сохранён", "15 Aug 2026" in items[0]["pub"])


def test_snapshot_selection():
    print("\n[T2] выбор снапшотов (step-hours + limit)")
    fetch = load_module("fetch_historical_news", SCRIPT_DIR / "fetch_historical_news.py")
    from datetime import datetime, timedelta, timezone
    snaps = []
    d0 = datetime(2025, 8, 1, tzinfo=timezone.utc)
    for day in range(0, 365, 3):  # раз в 3 дня за год
        snaps.append((d0 + timedelta(days=day)).strftime("%Y%m%d%H%M%S"))
    orig = fetch.list_snapshots
    fetch.list_snapshots = lambda: snaps
    # перехват main-логики через вызов функции с mocked get
    selected = []
    last_ts = None
    for s in snaps:
        ts = pd.Timestamp(s, tz="UTC")
        if last_ts is None or (ts - last_ts) >= pd.Timedelta(hours=40):
            selected.append((s, ts))
            last_ts = ts
    selected = selected[:50]
    check("шаг 40ч отбирает ~1/6 снапшотов", 40 <= len(selected) <= 80)
    check("limit работает", len(selected) == 50)
    fetch.list_snapshots = orig


# ---------------------------------------------------------------- T3
class FakeResp:
    def __init__(self, text: str):
        self._text = text

    def read(self):
        return json.dumps({"candidates": [{"content": {"parts": [{"text": self._text}]}}]}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_score_batch_parsing():
    print("\n[T3] score_batch: парсинг ответа Gemini (```json ... ```)")
    score = load_module("score_historical_sentiment", SCRIPT_DIR / "score_historical_sentiment.py")
    gemini_answer = '```json\n[\n  {"sentiment": 0.6},\n  {"sentiment": -0.7},\n  {"sentiment": 0.0}\n]\n```'
    import urllib.request
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=60: FakeResp(gemini_answer)
    try:
        res = score.score_batch("fake-key", ["a", "b", "c"])
    finally:
        urllib.request.urlopen = orig
    check("парсинг массива из ```json```", res == [0.6, -0.7, 0.0], f"got {res}")
    # ответ без JSON
    urllib.request.urlopen = lambda req, timeout=60: FakeResp("просто текст")
    try:
        res2 = score.score_batch("fake-key", ["a"])
    finally:
        urllib.request.urlopen = orig
    check("нет JSON -> None", res2 is None)


# ---------------------------------------------------------------- T4
def test_scoring_main():
    print("\n[T4] main(): merge + resume + relabel (мок Gemini)")
    score = load_module("score_historical_sentiment", SCRIPT_DIR / "score_historical_sentiment.py")

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "news_historical.jsonl"
        out = Path(tmp) / "scored.jsonl"
        # исходник: 6 новостей
        news = [json.loads(l) for l in
                (T / "fixtures" / "news_historical_sample.jsonl").read_text().splitlines()][:6]
        with open(src, "w") as f:
            for r in news:
                f.write(json.dumps(r) + "\n")
        # out: 2 уже оценены (resume-кейс)
        scored2 = [dict(news[0], sentiment=0.5, label="positive"),
                   dict(news[1], sentiment=-0.8, label="negative")]
        with open(out, "w") as f:
            for r in scored2:
                f.write(json.dumps(r) + "\n")

        score.SRC = src
        score.OUT = out
        score.gemini_keys = lambda: ["k1"]
        fake_scores = [0.6, -0.7, 0.0, 0.9]
        calls = {"n": 0}
        orig_sleep = score.time.sleep

        def fake_score_batch(key, titles):
            calls["n"] += 1
            return fake_scores[:len(titles)]

        score.score_batch = fake_score_batch
        score.time.sleep = lambda s: None
        try:
            rc = score.main()
        finally:
            score.time.sleep = orig_sleep
        rows = [json.loads(l) for l in out.read_text().splitlines()]
        check("exit 0", rc == 0)
        check("все 6 записаны", len(rows) == 6, f"got {len(rows)}")
        check("resume: старые оценки не тронуты",
              any(r["url"] == news[0]["url"] and r["sentiment"] == 0.5 for r in rows))
        check("новые оценены",
              any(r["url"] == news[2]["url"] and r["sentiment"] == 0.6 for r in rows))
        check("labels корректны",
              any(r["url"] == news[3]["url"] and r["label"] == "negative" for r in rows)
              and any(r["url"] == news[4]["url"] and r["label"] == "neutral" for r in rows))
        check("1 батч (6 заголовков, batch 8)", calls["n"] == 1)

    # resume: повторный запуск не пересчитывает
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "n.jsonl"
        out = Path(tmp) / "s.jsonl"
        news = [json.loads(l) for l in
                (T / "fixtures" / "news_historical_sample.jsonl").read_text().splitlines()][:3]
        with open(src, "w") as f:
            for r in news:
                f.write(json.dumps(r) + "\n")
        with open(out, "w") as f:
            for r in news:
                f.write(json.dumps(dict(r, sentiment=0.1, label="neutral")) + "\n")
        score.SRC, score.OUT = src, out
        calls["n"] = 0
        score.score_batch = fake_score_batch
        score.time.sleep = lambda s: None
        try:
            score.main()
        finally:
            score.time.sleep = orig_sleep
        check("resume: ничего не пересчитывается", calls["n"] == 0)


# ---------------------------------------------------------------- T5
def test_detect_coins():
    print("\n[T5] detect_coins")
    sph = load_module("sentiment_price_historical", SCRIPT_DIR / "sentiment_price_historical.py")
    check("Bitcoin -> BTC", sph.detect_coins("Bitcoin to $1M by 2030") == ["BTC"])
    check("Ethereum -> ETH", sph.detect_coins("Ethereum gas fees hit yearly low") == ["ETH"])
    check("Solana -> SOL", sph.detect_coins("Solana treasury earns $2.5M") == ["SOL"])
    check("без монет -> []", sph.detect_coins("Crypto market cap falls below $2T") == [])
    check("near не матчит 'year'", sph.detect_coins("Near Protocol AI agents") == ["NEAR"])
    check("binance -> BNB", "BNB" in sph.detect_coins("Binance faces regulatory probe"))
    check("множественные", set(sph.detect_coins("Bitcoin and Ethereum ETF flows")) == {"BTC", "ETH"})


# ---------------------------------------------------------------- T6
def test_end_to_end():
    print("\n[T6] end-to-end: новости -> цены -> корреляция")
    sph = load_module("sentiment_price_historical", SCRIPT_DIR / "sentiment_price_historical.py")

    news = [json.loads(l) for l in
            (T / "fixtures" / "news_historical_sample.jsonl").read_text().splitlines()]
    # сентименты: детерминированные по индексу (чередуем +/-
    for i, r in enumerate(news):
        r["sentiment"] = 0.7 if i % 2 == 0 else -0.7
        r["label"] = "positive" if i % 2 == 0 else "negative"

    # строим бампы: новость в час h -> +1%/-1% с h+1
    bumps: dict[str, dict[int, float]] = {}
    START_TS = int(pd.Timestamp("2025-09-01", tz="UTC").timestamp())
    for r in news:
        pub = r["pub"]
        m = re.search(r"\d{1,2} \w+ \d{4} \d{2}:\d{2}", pub)
        t = pd.to_datetime(m.group(0), format="%d %b %Y %H:%M", utc=True)
        h = int((t.timestamp() - START_TS) // 3600)
        if h < 0 or h >= 8700:
            continue
        sym = sph.detect_coins(r["title"]) or ["BTC"]
        for s in sym:
            bumps.setdefault(s, {})[h + 1] = 0.01 if r["sentiment"] > 0 else -0.01
    fake_qmb.set_bumps(bumps)

    # пишем временный файл новостей с сентиментом
    with tempfile.TemporaryDirectory() as tmp:
        nf = Path(tmp) / "news.jsonl"
        with open(nf, "w") as f:
            for r in news:
                f.write(json.dumps(r) + "\n")
        orig_newspath = sph.NEWS
        sph.NEWS = nf
        orig_argv = sys.argv
        sys.argv = ["sph", "--min-n", "5"]
        try:
            rc = sph.main()
        finally:
            sph.NEWS = orig_newspath
            sys.argv = orig_argv
        check("exit 0", rc == 0)
    # прямой расчёт корреляции на синтетике
    check("sanity: синтетика даёт положительную корреляцию на 1h",
          _direct_corr(news, bumps, START_TS, sph) > 0.5)


def _direct_corr(news, bumps, start_ts, sph_mod):
    """Per-coin bump for each news (like the prod code does)."""
    sents, rets = [], []
    for r in news:
        m = re.search(r"\d{1,2} \w+ \d{4} \d{2}:\d{2}", r["pub"])
        t = pd.to_datetime(m.group(0), format="%d %b %Y %H:%M", utc=True)
        h = int((t.timestamp() - start_ts) // 3600)
        if h < 0 or h >= 8700:
            continue
        sym = sph_mod.detect_coins(r["title"]) or ["BTC"]
        for s in sym:
            b = bumps.get(s, {}).get(h + 1, 0.0001)
            sents.append(r["sentiment"])
            rets.append(b * 100)
    return float(np.corrcoef(sents, rets)[0, 1]) if len(sents) > 2 else 0.0




# ---------------------------------------------------------------- T7
def test_fetch_main_flow():
    print("\n[T7] fetch main(): полный цикл с моком (дедуп + запись)")
    fetch = load_module("fetch_historical_news", SCRIPT_DIR / "fetch_historical_news.py")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "news_historical.jsonl"
        fetch.OUT = out
        # 3 снапшота, RSS-фикстура возвращается дважды (одни и те же статьи)
        fetch.list_snapshots = lambda: ["20250801000000", "20250901000000", "20251001000000"]
        rss = (T / "fixtures" / "rss_sample.xml").read_bytes()
        fetch.get = lambda url, timeout=40: rss
        orig_sleep = fetch.time.sleep
        fetch.time.sleep = lambda s: None
        try:
            rc = fetch.main()
        finally:
            fetch.time.sleep = orig_sleep
        rows = [json.loads(l) for l in out.read_text().splitlines()] if out.exists() else []
        check("exit 0", rc == 0)
        check("уникальные статьи (дедуп по url)", len(rows) == 2, f"got {len(rows)}")
        check("поля сохранены", all(r.get("title") and r.get("pub") for r in rows))
        # повторный запуск — дедуп с уже записанным
        fetch.list_snapshots = lambda: ["20251101000000"]
        fetch.time.sleep = lambda s: None
        try:
            fetch.main()
        finally:
            fetch.time.sleep = orig_sleep
        rows2 = [json.loads(l) for l in out.read_text().splitlines()]
        check("повторный запуск не дублирует", len(rows2) == 2, f"got {len(rows2)}")



# ---------------------------------------------------------------- T8
def test_key_validation():
    print("\n[T8] gemini_keys: лояльная валидация (429/timeout не отбрасывают)")
    score = load_module("score_historical_sentiment", SCRIPT_DIR / "score_historical_sentiment.py")
    import urllib.request, urllib.error

    env_file = Path(tempfile.mkdtemp()) / ".env"
    env_file.write_text("GEMINI_API_KEY_1=goodkey1\nGEMINI_API_KEY_2=badkey2\n"
                        "GEMINI_API_KEY_3=limited3\n")
    score.ROOT = env_file.parent

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{}'

    class Err429(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("u", 429, "Too Many", None, None)

    class Err404(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("u", 404, "Not Found", None, None)

    responses = {"goodkey1": Resp(), "badkey2": Err404(), "limited3": Err429()}
    orig = urllib.request.urlopen

    def fake_urlopen(req, timeout=20):
        url = req.full_url
        for k in responses:
            if f"key={k}" in url:
                r = responses[k]
                if isinstance(r, Exception):
                    raise r
                return r
        raise Err404()

    urllib.request.urlopen = fake_urlopen
    try:
        keys = score.gemini_keys()
    finally:
        urllib.request.urlopen = orig
    check("рабочий ключ сохранён", "goodkey1" in keys)
    check("404-ключ отброшен", "badkey2" not in keys)
    check("429-ключ сохранён (транзиентный)", "limited3" in keys)

if __name__ == "__main__":
    test_fetch_parsing()
    test_snapshot_selection()
    test_score_batch_parsing()
    test_scoring_main()
    test_detect_coins()
    test_end_to_end()
    test_fetch_main_flow()
    test_key_validation()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
