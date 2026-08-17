#!/usr/bin/env python3
"""Local lexicon-based sentiment scorer for crypto news headlines.

No external LLM needed: deterministic dictionary approach with negation and
amplifier handling, tuned for crypto vocabulary. Scores in [-1, 1].

Usage (as library):
    from news_local_sentiment import score_title, score_batch

CLI:
    python news_local_sentiment.py --file news_historical.jsonl --out scored.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

# --- lexicon: (word, weight) ---
POSITIVE = {
    # strong
    "surge": 0.8, "surges": 0.8, "surged": 0.8, "soar": 0.8, "soars": 0.8,
    "soared": 0.8, "rocket": 0.8, "explode": 0.8, "explodes": 0.8, "moon": 0.7,
    "record": 0.6, "all-time": 0.7, "milestone": 0.6, "breakthrough": 0.7,
    "rally": 0.7, "rallies": 0.7, "rallied": 0.7, "boom": 0.7, "skyrocket": 0.8,
    "ballistic": 0.6, "spike": 0.5, "spikes": 0.5, "jump": 0.5, "jumps": 0.5,
    "jumped": 0.5, "leap": 0.5, "gains": 0.5, "gain": 0.4, "gained": 0.4,
    "rise": 0.4, "rises": 0.4, "rose": 0.4, "risen": 0.4, "up": 0.2,
    "higher": 0.3, "high": 0.3, "strong": 0.4, "strongest": 0.5, "bullish": 0.6,
    "bull": 0.5, "bulls": 0.5, "bullrun": 0.7, "buy": 0.3, "buys": 0.3,
    "buying": 0.4, "accumulate": 0.4, "accumulation": 0.5, "inflow": 0.6,
    "inflows": 0.6, "adoption": 0.6, "adopted": 0.5, "adopts": 0.5,
    "approve": 0.6, "approved": 0.6, "approval": 0.6, "approves": 0.6,
    "launch": 0.4, "launches": 0.4, "launched": 0.4, "partnership": 0.5,
    "partners": 0.4, "integration": 0.4, "integrate": 0.4, "upgrade": 0.4,
    "upgrades": 0.4, "upgraded": 0.4, "support": 0.3, "supports": 0.3,
    "backed": 0.3, "endorsed": 0.4, "endorsement": 0.4, "win": 0.5,
    "wins": 0.5, "won": 0.5, "positive": 0.5, "profit": 0.5, "profitable": 0.5,
    "growth": 0.5, "growing": 0.5, "grow": 0.4, "expand": 0.4, "expansion": 0.4,
    "institutional": 0.4, "institutions": 0.4, "etf": 0.3, "etfs": 0.3,
    "green": 0.4, "optimistic": 0.5, "confidence": 0.4, "confident": 0.4,
    "hope": 0.3, "hopes": 0.3, "recovery": 0.5, "recovers": 0.5, "rebound": 0.6,
    "rebounds": 0.6, "bullish": 0.6, "beat": 0.4, "beats": 0.4, "outperform": 0.6,
    "outperforms": 0.6, "demand": 0.4, "huge": 0.4, "massive": 0.5,
    "flourish": 0.6, "thrive": 0.6, "gain ground": 0.5, "break out": 0.6,
    "breakout": 0.7, "mooning": 0.7, "pump": 0.5, "pumps": 0.5, "pumped": 0.5,
    "buyback": 0.5, "dividend": 0.4, "reward": 0.4, "rewards": 0.4,
    "staking": 0.3, "yield": 0.3, "yields": 0.3, "apy": 0.3, "hodl": 0.2,
    "long": 0.2, "bullishness": 0.6, "momentum": 0.4, "surpasses": 0.6,
    "surpassed": 0.6, "topping": 0.5, "tops": 0.4, "best": 0.5,
    # mild positive
    "good": 0.3, "great": 0.4, "better": 0.3, "improve": 0.4, "improves": 0.4,
    "improved": 0.4, "boost": 0.5, "boosts": 0.5, "boosted": 0.5, "stable": 0.2,
    "stability": 0.3, "steady": 0.3, "solid": 0.4, "healthy": 0.4,
}

NEGATIVE = {
    # strong
    "crash": -0.9, "crashes": -0.9, "crashed": -0.9, "plunge": -0.8,
    "plunges": -0.8, "plunged": -0.8, "tank": -0.8, "tanks": -0.8, "tanked": -0.8,
    "collapse": -0.8, "collapses": -0.8, "collapsed": -0.8, "dump": -0.7,
    "dumps": -0.7, "dumped": -0.7, "selloff": -0.7, "sell-off": -0.7,
    "selloff": -0.7, "bloodbath": -0.9, "wipeout": -0.8, "liquidation": -0.6,
    "liquidations": -0.6, "liquidated": -0.6, "hack": -0.8, "hacked": -0.8,
    "hacking": -0.7, "exploit": -0.7, "exploited": -0.7, "breach": -0.7,
    "stolen": -0.8, "steal": -0.7, "theft": -0.7, "scam": -0.8, "scams": -0.8,
    "fraud": -0.8, "ponzi": -0.9, "rug": -0.9, "rugpull": -0.9, "rug pull": -0.9,
    "bankrupt": -0.8, "bankruptcy": -0.8, "insolvent": -0.7, "ban": -0.7,
    "bans": -0.7, "banned": -0.7, "banned": -0.7, "prohibit": -0.6,
    "crackdown": -0.7, "crackdowns": -0.7, "lawsuit": -0.6, "lawsuits": -0.6,
    "sue": -0.5, "sued": -0.6, "sues": -0.5, "probe": -0.5, "probes": -0.5,
    "investigation": -0.5, "investigate": -0.5, "investigates": -0.5,
    "regulatory": -0.3, "regulation": -0.2, "bearish": -0.6, "bear": -0.5,
    "bears": -0.5, "bear market": -0.7, "drop": -0.5, "drops": -0.5,
    "dropped": -0.5, "fall": -0.4, "falls": -0.4, "fell": -0.4, "fallen": -0.4,
    "decline": -0.5, "declines": -0.5, "declined": -0.5, "down": -0.3,
    "lower": -0.3, "low": -0.2, "weak": -0.4, "weaker": -0.4, "weakest": -0.5,
    "outflow": -0.6, "outflows": -0.6, "sell": -0.3, "sells": -0.3,
    "selling": -0.4, "capitulate": -0.7, "capitulation": -0.7, "panic": -0.6,
    "fear": -0.5, "fears": -0.5, "worried": -0.4, "worry": -0.3, "risk": -0.3,
    "risks": -0.3, "risky": -0.4, "danger": -0.5, "dangerous": -0.5,
    "threat": -0.5, "threatens": -0.5, "warning": -0.4, "warns": -0.4,
    "warn": -0.3, "caution": -0.3, "reject": -0.5, "rejected": -0.5,
    "rejects": -0.5, "rejection": -0.5, "delay": -0.4, "delays": -0.4,
    "delayed": -0.4, "postpone": -0.5, "postponed": -0.5, "fail": -0.5,
    "fails": -0.5, "failed": -0.5, "failure": -0.5, "loss": -0.4,
    "losses": -0.5, "loses": -0.5, "lost": -0.5, "lose": -0.4, "debt": -0.3,
    "deficits": -0.4, "deficit": -0.4, "downgrade": -0.6, "downgraded": -0.6,
    "negative": -0.5, "red": -0.3, "dead": -0.5, "death": -0.6, "die": -0.5,
    "dying": -0.5, "kills": -0.5, "killed": -0.5, "crisis": -0.6,
    "recession": -0.5, "bubble": -0.4, "burst": -0.5, "worst": -0.5,
    "slump": -0.7, "slumps": -0.7, "slumped": -0.7, "slip": -0.4, "slips": -0.4,
    "squeeze": -0.4, "short": -0.2, "shorts": -0.3, "shorting": -0.4,
    "pressure": -0.3, "pressured": -0.4, "bleed": -0.5, "bleeds": -0.5,
    "blood": -0.6, "wipe": -0.6, "wipes": -0.6, "evaporat": -0.6,
    "disappoint": -0.5, "disappointed": -0.5, "miss": -0.3, "misses": -0.3,
    "cut": -0.3, "cuts": -0.3, "slashed": -0.5, "slash": -0.5,
    "halt": -0.5, "halts": -0.5, "halted": -0.5, "suspend": -0.5,
    "suspended": -0.5, "freeze": -0.4, "frozen": -0.5, "exit": -0.3,
    "exits": -0.3, "leaves": -0.3, "flee": -0.5, "flees": -0.5,
    "withdraw": -0.3, "withdraws": -0.3, "withdrew": -0.4, "shutdown": -0.5,
    "shuts": -0.5, "closed": -0.3, "closes": -0.3, "cease": -0.5,
    # добавочные из расхождений с Gemini
    "impossible": -0.6, "impossibility": -0.5, "lows": -0.3, "cleanout": -0.6,
    "headwinds": -0.5, "weigh": -0.3, "weighs": -0.3, "weighted": -0.3,
    "teeters": -0.4, "teetering": -0.4, "shuttered": -0.5, "shutters": -0.5,
    "cancels": -0.5, "cancelled": -0.5, "cancellation": -0.5, "postpones": -0.5,
    "pauses": -0.5, "paused": -0.5, "pausing": -0.4, "restrict": -0.4,
    "restricts": -0.4, "restrictions": -0.4, "restricted": -0.4,
    "exclude": -0.4, "exclusion": -0.4, "excluded": -0.4, "hidden": -0.3,
    "masks": -0.3, "masked": -0.3, "burn": -0.4, "burns": -0.4,
    "register": -0.3, "registers": -0.3, "slips": -0.4, "slid": -0.4,
    "slide": -0.4, "fades": -0.2, "fading": -0.2, "dim": -0.3, "cloudy": -0.3,
    "trouble": -0.4, "troubled": -0.4, "strain": -0.3, "strained": -0.3,
    "untested": -0.3, "unclear": -0.3, "uncertainty": -0.3, "uncertain": -0.3,
    "overhang": -0.4, "overhangs": -0.4, "doubt": -0.3, "doubts": -0.3,
    "skeptic": -0.3, "skeptical": -0.3, "backlash": -0.5, "resistance": -0.2,
    "struggle": -0.4, "struggles": -0.4, "struggling": -0.4, "lag": -0.3,
    "lags": -0.3, "underperform": -0.5, "underperforms": -0.5,
}

NEGATIONS = {"not", "no", "never", "without", "isn't", "aren't", "won't", "cannot",
             "can't", "doesn't", "don't", "didn't", "hardly", "barely", "denies",
             "deny", "dismisses", "dismiss"}

AMPLIFIERS = {"record": 1.5, "all-time": 1.5, "massive": 1.4, "huge": 1.3,
              "extreme": 1.4, "severe": 1.4, "sharp": 1.3, "steep": 1.3,
              "major": 1.2, "significant": 1.2, "big": 1.2, "biggest": 1.4,
              "worst": 1.3, "total": 1.2, "complete": 1.2, "historic": 1.3}

_TOKEN_RE = re.compile(r"[a-z0-9'\-]+")

# merged word->weight (positive/negative merged; negative keep sign)
_LEXICON: dict[str, float] = {}
_LEXICON.update(POSITIVE)
for w, v in NEGATIVE.items():
    _LEXICON[w] = v


def score_title(title: str) -> float:
    """Lexicon sentiment score in [-1, 1] with negation & amplifier handling."""
    tokens = _TOKEN_RE.findall(title.lower())
    if not tokens:
        return 0.0
    score = 0.0
    weight_sum = 0.0
    negate_next = False
    for i, tok in enumerate(tokens):
        # multi-word phrases first (e.g. "rug pull", "bear market")
        phrase = None
        if i + 1 < len(tokens):
            cand = f"{tok} {tokens[i + 1]}"
            if cand in _LEXICON:
                phrase = cand
        word = phrase or tok
        if word in NEGATIONS:
            negate_next = True
            continue
        w = _LEXICON.get(word)
        if w is None:
            continue
        if negate_next:
            w = -w
            negate_next = False
        amp = 1.0
        # amplifier = previous token
        if i > 0 and tokens[i - 1] in AMPLIFIERS:
            amp = AMPLIFIERS[tokens[i - 1]]
        score += w * amp
        weight_sum += abs(w * amp)
    if weight_sum == 0:
        return 0.0
    raw = score / weight_sum  # in [-1, 1]
    # saturation: single weak word should not yield full score
    factor = min(1.0, weight_sum / 1.5)
    return max(-1.0, min(1.0, raw * factor))


def score_batch(titles: list[str]) -> list[float]:
    return [score_title(t) for t in titles]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, required=True,
                    help="input jsonl with 'title' fields")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.file.read_text().splitlines() if l]
    t0 = time.time()
    n = 0
    for r in rows:
        s = score_title(r.get("title", ""))
        r["sentiment"] = round(s, 3)
        r["label"] = "positive" if s > 0.2 else ("negative" if s < -0.2 else "neutral")
        r["scorer"] = "local_lexicon"
        n += 1
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    pos = sum(1 for r in rows if r["sentiment"] > 0.2)
    neg = sum(1 for r in rows if r["sentiment"] < -0.2)
    print(f"оценено: {n} за {time.time()-t0:.2f}s | pos {pos} / neg {neg} / neu {n-pos-neg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
