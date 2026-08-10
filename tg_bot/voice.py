"""Голосовые ответы и транскрибация (выделено из run_telegram_bot.py)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _safe


VOICE_REPLY_FILE = PROJECT_ROOT / "data" / "voice_reply.json"


def _voice_enabled(chat_id: int) -> bool:
    try:
        return bool(json.loads(VOICE_REPLY_FILE.read_text(encoding="utf-8")).get(str(chat_id), False))
    except Exception:
        return False


def _set_voice_enabled(chat_id: int, on: bool) -> None:
    try:
        cfg = json.loads(VOICE_REPLY_FILE.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    cfg[str(chat_id)] = on
    VOICE_REPLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_REPLY_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _send_voice_reply(api, chat_id: int, text: str) -> bool:
    """Озвучить текст через gTTS и отправить голосовое."""
    try:
        from gtts import gTTS
    except ImportError:
        return False
    clean = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
    clean = clean.replace("&amp;", "и").replace("&lt;", "<").replace("&gt;", ">")[:1500]
    try:
        tts = gTTS(text=clean, lang="ru")
        path = f"/tmp/aios_voice_reply_{int(time.time() * 1000)}.mp3"
        tts.save(path)
        api.send_voice(chat_id, path)
        return True
    except Exception as e:
        print(f"  [VOICE-REPLY] err: {e}")
        return False


def _transcribe_audio(path: str) -> str:
    """Распознать голосовое или аудиозапись через AIOS Whisper & Neural Diarization Engine."""
    try:
        from aios_core.whisper_colab_transcriber import transcribe_audio_call, generate_call_summary
        from aios_core.google_contacts_sync import match_folder_to_google_contact
        from aios_core.neural_diarization import perform_neural_diarization, format_diarized_transcript_text
        from aios_core.call_task_extractor import extract_and_save_call_tasks

        res = transcribe_audio_call(path)
        if res and res.get("status") == "success":
            text = res.get("transcription", "")
            segs = res.get("segments", [])
            c_info = match_folder_to_google_contact("Голосовое Telegram")
            d_segs = perform_neural_diarization(path, segs, c_info, is_dictaphone=True)
            formatted_text = format_diarized_transcript_text(d_segs) or text
            
            # Сохраняем в Calls
            fname = os.path.basename(path)
            stem = os.path.splitext(fname)[0]
            summary = generate_call_summary(formatted_text, fname)
            
            # Извлекаем CRM задачи
            extract_and_save_call_tasks(stem, fname, summary, "Голосовое Telegram")
            return formatted_text
    except Exception as e:
        print(f"  [WHISPER-VOICE] err: {e}")
    import base64
    import urllib.request as _urllib

    try:
        data_b64 = base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return ""

    keys = [os.environ.get("GEMINI_API_KEY", "")]
    for i in (1, 2, 3):
        keys.append(os.environ.get(f"GEMINI_API_KEY_{i}", ""))
    keys = [k for k in keys if k]

    mime = "audio/ogg" if path.lower().endswith((".ogg", ".oga", ".opus")) else "audio/mpeg"
    for model in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite",
                  "gemini-2.5-flash-lite", "gemini-flash-latest"):
        for key in keys:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{"parts": [
                        {"inline_data": {"mime_type": mime, "data": data_b64}},
                        {"text": "Распознай речь дословно. Верни только распознанный текст, без пояснений."},
                    ]}],
                }).encode()
                req = _urllib.Request(url, data=payload,
                                      headers={"Content-Type": "application/json"})
                with _urllib.urlopen(req, timeout=60) as resp:
                    out = json.loads(resp.read())
                cands = out.get("candidates") or []
                if cands:
                    txt = (cands[0].get("content", {}).get("parts") or [{}])[0].get("text", "").strip()
                    if txt:
                        return txt
            except Exception as e:
                print(f"  [VOICE] {model} err: {str(e)[:120]}")
                continue
    return ""
