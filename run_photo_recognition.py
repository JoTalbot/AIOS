#!/usr/bin/env python3
"""
AIOS Photo Recognition — распознаёт запчасть по фото через Gemini vision:
что это, состояние, примерная цена, совместимость.
  python run_photo_recognition.py <путь_к_фото>
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _gemini_keys() -> list[str]:
    keys = []
    for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        v = _env(k)
        if v:
            keys.append(v)
    return keys


def recognize(photo_path: str) -> dict:
    """Распознать запчасть по фото (Gemini vision)."""
    if not Path(photo_path).exists():
        return {"status": "error", "error": f"Файл не найден: {photo_path}"}
    try:
        data_b64 = base64.b64encode(Path(photo_path).read_bytes()).decode()
    except Exception as e:
        return {"status": "error", "error": f"Не удалось прочитать фото: {e}"}

    mime = "image/jpeg"
    if photo_path.lower().endswith(".png"):
        mime = "image/png"
    elif photo_path.lower().endswith(".webp"):
        mime = "image/webp"

    prompt = (
        "Это фото автозапчасти. Определи: 1) что это за деталь (название, марка/модель если видно), "
        "2) примерное состояние (новая/б/у, дефекты), 3) примерную цену в гривнах, "
        "4) с какими авто совместима (если видно маркировку). "
        "Верни ТОЛЬКО JSON: {\"part\": \"название\", \"condition\": \"...\", "
        "\"price\": число, \"compatible\": \"...\", \"notes\": \"краткие заметки\"}. По-русски."
    )

    for model in ("gemini-2.5-flash", "gemini-2.0-flash"):
        for key in _gemini_keys():
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{"parts": [
                        {"inline_data": {"mime_type": mime, "data": data_b64}},
                        {"text": prompt},
                    ]}],
                }).encode()
                req = urllib.request.Request(url, data=payload,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    out = json.loads(resp.read())
                cands = out.get("candidates") or []
                if cands:
                    txt = (cands[0].get("content", {}).get("parts") or [{}])[0].get("text", "")
                    start = txt.find("{")
                    end = txt.rfind("}") + 1
                    if start >= 0 and end > start:
                        d = json.loads(txt[start:end])
                        d.setdefault("part", "не определено")
                        d.setdefault("condition", "")
                        d.setdefault("price", None)
                        d.setdefault("compatible", "")
                        d.setdefault("notes", "")
                        return {"status": "ok", **d, "photo": photo_path}
                    return {"status": "error", "error": "Модель не вернула JSON", "raw": txt[:200]}
            except Exception as e:
                print(f"  [PHOTO-REC] {model} err: {str(e)[:100]}")
                continue
    return {"status": "error", "error": "Gemini недоступен"}


def main() -> None:
    photo = sys.argv[1] if len(sys.argv) > 1 else ""
    if not photo:
        print(json.dumps({"status": "error", "error": "Укажите путь к фото"}))
        return
    print(json.dumps(recognize(photo), ensure_ascii=False))


if __name__ == "__main__":
    main()
