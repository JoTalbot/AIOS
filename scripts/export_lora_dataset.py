#!/usr/bin/env python3
"""
AIOS - Экспорт LoRA-датасета (Этап 3)

Собирает примеры из разных источников AIOS в единый датасет формата OpenAI
messages (совместим с Unsloth / chat template):

  - существующий data/finetune/aios_coder_hf.jsonl
  - data/finetune/aios_coder_dataset.jsonl (инструкции -> конвертация)
  - data/templates/** (шаблоны ответов/предложений) -> примеры "assistant"
  - data/Calls/** (коммерческие ответы/сделки) если есть

Выход: data/finetune/lora_commercial.jsonl
"""

from __future__ import annotations

import sys
import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FINETUNE = REPO_ROOT / "data" / "finetune"
TEMPLATES = REPO_ROOT / "data" / "templates"
OUT = FINETUNE / "lora_commercial.jsonl"

SYSTEM = (
    "You are AIOS CommercialAssistant, an expert in writing winning freelance "
    "proposals, commercial offers, and professional responses. Style: concise, "
    "confident, value-driven, with clear deliverables and pricing."
)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def to_messages_hf(ex: dict) -> dict | None:
    """Конвертация aios_coder_hf (уже messages) или instruction/input/output."""
    if "messages" in ex:
        return ex
    if "instruction" in ex:
        user = ex.get("instruction", "")
        inp = ex.get("input", "")
        content = user + (f"\n{inp}" if inp else "")
        return {
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": content},
                {"role": "assistant", "content": ex.get("output", "")},
            ]
        }
    return None


def collect_templates() -> list[dict]:
    """Шаблоны из data/templates как примеры ассистента."""
    out = []
    if not TEMPLATES.exists():
        return out
    for p in TEMPLATES.rglob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            text = it.get("text") or it.get("content") or it.get("body") or ""
            if isinstance(text, str) and len(text) > 40:
                out.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": "Напиши коммерческое предложение / ответ клиенту."},
                        {"role": "assistant", "content": text},
                    ]
                })
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="AIOS LoRA dataset export")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    examples = []
    examples += [to_messages_hf(e) for e in load_jsonl(FINETUNE / "aios_coder_hf.jsonl")]
    examples += [to_messages_hf(e) for e in load_jsonl(FINETUNE / "aios_coder_dataset.jsonl")]
    examples += collect_templates()
    examples = [e for e in examples if e]

    random.seed(args.seed)
    random.shuffle(examples)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"✅ Экспортировано {len(examples)} примеров -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
