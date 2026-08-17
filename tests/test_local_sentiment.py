#!/usr/bin/env python3
"""Tests for the local lexicon sentiment scorer (before prod deploy)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))

from news_local_sentiment import score_title, score_batch

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


def test_positive():
    print("\n[L1] позитивные заголовки -> score > 0")
    cases = [
        ("Bitcoin surges to new all-time high as ETF inflows soar", True),
        ("Ethereum rallies on record institutional adoption", True),
        ("Solana launches major partnership with Fortune 500", True),
        ("Crypto market rebounds strongly, bulls in control", True),
    ]
    for title, want_pos in cases:
        s = score_title(title)
        check(f"'{title[:45]}...' -> {s:+.2f}", s > 0.2 if want_pos else s < -0.2, f"got {s}")


def test_negative():
    print("\n[L2] негативные заголовки -> score < 0")
    cases = [
        ("Bitcoin crashes below $50k amid panic selloff", True),
        ("Ethereum hacked, $100M stolen in exploit", True),
        ("Binance faces regulatory crackdown and lawsuit", True),
        ("Crypto market plunges, liquidations wipe out traders", True),
    ]
    for title, want_neg in cases:
        s = score_title(title)
        check(f"'{title[:45]}...' -> {s:+.2f}", s < -0.2 if want_neg else s > 0.2, f"got {s}")


def test_neutral():
    print("\n[L3] нейтральные -> |score| мал")
    for title in ["CoinDesk launches new podcast series",
                  "Ethereum developers schedule monthly call",
                  "Crypto exchange announces new office hours"]:
        s = score_title(title)
        check(f"'{title[:45]}...' -> {s:+.2f}", abs(s) <= 0.3, f"got {s}")


def test_negation():
    print("\n[L4] отрицания инвертируют")
    s1 = score_title("Bitcoin does not crash, holds steady above support")
    s2 = score_title("Bitcoin not in danger, analysts say")
    check(f"'does not crash' -> {s1:+.2f}", s1 > -0.2, f"got {s1}")
    check(f"'not in danger' -> {s2:+.2f}", s2 > -0.2, f"got {s2}")


def test_amplifier():
    print("\n[L5] усилители (record/massive)")
    s1 = score_title("Bitcoin rises")
    s2 = score_title("Bitcoin surges to record high")
    check(f"усиленный сильнее: {s1:+.2f} vs {s2:+.2f}", s2 > s1, f"got {s1} {s2}")


def test_real_headlines():
    print("\n[L6] реальные заголовки из фикстуры (sanity)")
    rows = [json.loads(l) for l in
            (T / "fixtures" / "news_historical_sample.jsonl").read_text().splitlines()]
    scores = [score_title(r["title"]) for r in rows]
    n_pos = sum(1 for s in scores if s > 0.2)
    n_neg = sum(1 for s in scores if s < -0.2)
    check(f"смесь знаков (pos {n_pos}, neg {n_neg} из {len(rows)})",
          n_pos > 0 and n_neg > 0)
    check("в диапазоне [-1,1]", all(-1 <= s <= 1 for s in scores))


def test_consistency_deterministic():
    print("\n[L7] детерминированность и батч")
    titles = ["Bitcoin surges", "Ethereum hacked", "Market flat today"]
    a = score_batch(titles)
    b = score_batch(titles)
    check("одинаковые результаты", a == b)


def test_performance():
    print("\n[L8] производительность (1545 заголовков)")
    # генерируем 1545 синтетических
    titles = [f"Bitcoin {'surges' if i % 2 else 'crashes'} in week {i}" for i in range(1545)]
    t0 = time.time()
    for t in titles:
        score_title(t)
    dt = time.time() - t0
    check(f"1545 заголовков за {dt:.2f}s (< 5s)", dt < 5.0)


def test_empty_edge():
    print("\n[L9] крайние случаи")
    check("пустая строка -> 0", score_title("") == 0.0)
    check("только цифры -> 0", score_title("123 456") == 0.0)
    check("не-ASCII безопасно", -1 <= score_title("Биткоин вырос, эфир упал") <= 1)


if __name__ == "__main__":
    test_positive()
    test_negative()
    test_neutral()
    test_negation()
    test_amplifier()
    test_real_headlines()
    test_consistency_deterministic()
    test_performance()
    test_empty_edge()
    print(f"\n===== ИТОГ: PASS {PASS} / FAIL {FAIL} =====")
    sys.exit(1 if FAIL else 0)
