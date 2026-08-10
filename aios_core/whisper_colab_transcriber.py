#!/usr/bin/env python3
"""
AIOS Whisper Colab Transcriber Engine
Модуль расшифровки аудио и телефонных звонков с использованием бесплатного Google Colab GPU (Whisper Large-v3)
и локального резервного fallback (faster-whisper CPU).
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

WHISPER_URL_FILE = REPO_ROOT / "data" / "colab_whisper_url.json"
CALLS_DIR = REPO_ROOT / "Calls"

logger = logging.getLogger("aios.whisper_transcriber")


def get_colab_whisper_url() -> Optional[str]:
    """Возвращает текущий зарегистрированный URL Colab Whisper."""
    if WHISPER_URL_FILE.exists():
        try:
            with open(WHISPER_URL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("url")
        except Exception:
            pass

    env_url = os.getenv("COLAB_WHISPER_URL")
    if env_url:
        return env_url
    return None


def check_colab_whisper_health() -> Dict[str, Any]:
    """Проверяет доступность Colab Whisper GPU сервера или локального движка."""
    url = get_colab_whisper_url()
    if url:
        try:
            resp = requests.get(f"{url.rstrip('/')}/health", timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                res["online"] = True
                res["url"] = url
                res["provider"] = "colab_gpu"
                return res
        except Exception:
            pass

    # Резервный локальный движок на VPS
    return {
        "online": True,
        "provider": "local_cpu",
        "model": "faster-whisper",
        "url": "local://vps",
        "reason": "Локальный модуль на процессоре VPS активен"
    }


def transcribe_file_colab(file_path: str, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Отправляет файл на транскрибацию в Colab Whisper GPU API."""
    url = get_colab_whisper_url()
    if not url:
        return None

    file_path = str(file_path)
    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return None

    endpoint = f"{url.rstrip('/')}/transcribe"
    params = {}
    if language:
        params["language"] = language

    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            resp = requests.post(endpoint, files=files, params=params, timeout=300)

        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"Colab Whisper ответил со статусом {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        logger.warning(f"Ошибка запроса к Colab Whisper: {e}")
        return None


def transcribe_file_local_fallback(file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Локальный резервный транскрибатор на базе faster-whisper CPU."""
    logger.info(f"Запуск локального fallback-транскрибатора (CPU) для файла: {file_path}")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments_gen, info = model.transcribe(
            str(file_path),
            language=language if language and language != "auto" else None,
            vad_filter=True
        )

        segments = []
        full_text_list = []
        for seg in segments_gen:
            full_text_list.append(seg.text.strip())
            segments.append({
                "id": seg.id,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip()
            })

        full_text = " ".join(full_text_list)
        return {
            "status": "success",
            "provider": "local_cpu_fallback",
            "filename": os.path.basename(file_path),
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_seconds": round(info.duration, 2),
            "transcription": full_text,
            "segments_count": len(segments),
            "segments": segments
        }
    except Exception as e:
        logger.error(f"Ошибка локального fallback транскрибирования: {e}")
        return {
            "status": "error",
            "error": str(e),
            "transcription": f"[Ошибка транскрибации: {e}]"
        }


def transcribe_audio_call(file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Единая точка входа транскрибации: пробует Colab GPU, при ошибке переключается на Local CPU."""
    # 1. Попытка Colab GPU
    colab_res = transcribe_file_colab(file_path, language=language)
    if colab_res and colab_res.get("status") == "success":
        colab_res["provider"] = "colab_gpu_large_v3"
        return colab_res

    # 2. Переключение на локальный fallback
    return transcribe_file_local_fallback(file_path, language=language)


def generate_call_summary(transcription_text: str, filename: str) -> str:
    """Генерирует исполнительское резюме звонка с помощью LLM AIOS."""
    if not transcription_text or len(transcription_text.strip()) < 5:
        return "❌ Недостаточно текста для генерации аналитического резюме."

    prompt = f"""
Проанализируй транскрибированный телефонный звонок / аудиозапись ({filename}):

Текст звонка:
\"\"\"
{transcription_text}
\"\"\"

Составь структурированный отчет на русском языке по следующему формату:
📌 **Тема разговора**: (1-2 предложения)
👥 **Участники и роли**: (кто звонил, суть обращения)
💡 **Ключевые тезисы и договоренности**: (по пунктам)
🎯 **Следующие шаги / Action Items**: (что нужно сделать по итогам звонка)
🎭 **Тональность общения**: (Позитивная / Нейтральная / Напряженная)
"""
    try:
        from aios_core.llm_balancer import LLMBalancer
        from aios_core.google_contacts_sync import match_folder_to_google_contact
        from aios_core.speaker_diarization import diarize_audio_segments, format_diarized_transcript_text
        balancer = LLMBalancer()
        res_text = balancer.chat(
            messages=[{"role": "user", "content": prompt}],
            system="Ты — экспертный ИИ-аналитик телефонных звонков и CRM системы AIOS."
        )
        if res_text:
            return res_text.strip()
    except Exception as e:
        logger.warning(f"Ошибка генерации LLM-резюме: {e}")

    return f"📌 **Транскрипция звонка**: {transcription_text[:300]}..."


def process_calls_directory(dir_path: str = str(CALLS_DIR), force: bool = False) -> List[Dict[str, Any]]:
    """
    Сканирует папку /root/AIOS/Calls, расшифровывает новые аудиофайлы,
    сохраняет .txt, .json и _summary.md резюме.
    """
    target_dir = Path(dir_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    supported_exts = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".3gp", ".amr"}
    results = []

    audio_files = [f for f in target_dir.rglob("*") if f.is_file() and f.suffix.lower() in supported_exts]

    for audio_file in audio_files:
        stem = audio_file.stem
        txt_path = target_dir / f"{stem}.txt"
        json_path = target_dir / f"{stem}.json"
        summary_path = target_dir / f"{stem}_summary.md"

        if not force and txt_path.exists() and json_path.exists():
            logger.info(f"Пропуск уже обработанного файла: {audio_file.name}")
            continue

        logger.info(f"🎙️ Обработка звонка: {audio_file.name}...")
        result = transcribe_audio_call(str(audio_file))

        # 1. Сопоставление с Google Контактом по имени папки
        folder_name = audio_file.parent.name if audio_file.parent != CALLS_DIR else audio_file.stem
        is_dictaphone = "!voice" in str(audio_file) or "voice" in audio_file.name.lower()
        if is_dictaphone and folder_name == "!voice":
            folder_name = "Запись окружения (Диктофон)"

        contact_info = match_folder_to_google_contact(folder_name)
        result["google_contact"] = contact_info
        result["is_dictaphone"] = is_dictaphone
        result["folder_name"] = folder_name

        # 2. Распознавание спикеров (Diarization)
        raw_segments = result.get("segments", [])
        diarized_segments = diarize_audio_segments(raw_segments, contact_info, is_dictaphone=is_dictaphone)
        result["diarized_segments"] = diarized_segments
        diarized_text = format_diarized_transcript_text(diarized_segments)

        # Сохранение текста с разметкой спикеров
        transcription_text = result.get("transcription", "")
        txt_path.write_text(diarized_text or transcription_text, encoding="utf-8")

        # Сохранение полной метаинформации
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Генерация и сохранение AI-резюме
        summary = generate_call_summary(transcription_text, audio_file.name)
        summary_path.write_text(summary, encoding="utf-8")

        result["txt_path"] = str(txt_path)
        result["json_path"] = str(json_path)
        result["summary_path"] = str(summary_path)
        result["summary"] = summary
        results.append(result)

        # Telegram утилита отправки уведомления при обработке
        try:
            _send_tg_call_notification(audio_file.name, result, summary)
        except Exception as e:
            logger.warning(f"Ошибка отправки TG-уведомления по звонку: {e}")

    return results


def _send_tg_call_notification(filename: str, result: Dict[str, Any], summary: str):
    """Отправляет сведение о новом обработанном звонке в Telegram."""
    try:
        from tg_bot.treasury import _send_tg_message
        provider = "⚡ Colab T4 GPU (Whisper Large-v3)" if "colab" in result.get("provider", "") else "💻 Local CPU (Fallback)"
        duration = result.get("duration_seconds", 0)
        lang = result.get("language", "авто")

        msg = (
            f"📞 **[AIOS Calls Brain] Расшифрован звонок!**\n\n"
            f"📂 **Файл**: `{filename}`\n"
            f"⏱ **Длительность**: `{duration} сек` | **Язык**: `{lang}`\n"
            f"⚙️ **Движок**: {provider}\n\n"
            f"{summary}\n\n"
            f"📄 *Полный текст сохранен в Calls/{filename}.txt*"
        )
        _send_tg_message(msg)
    except Exception as e:
        logger.debug(f"TG notify error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== AIOS Whisper Colab Transcriber Status ===")
    status = check_colab_whisper_health()
    print(f"Colab GPU Status: {status}")

    print("\n=== Обработка папки Calls ===")
    processed = process_calls_directory()
    print(f"Обработано новых файлов: {len(processed)}")
