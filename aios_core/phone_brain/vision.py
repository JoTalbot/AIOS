"""VLM-локатор элементов экрана (этап 3): Gemini API → fallback OpenRouter.

Нужен для самовосстановления селекторов: когда вся fallback-цепочка skill'а
не находит элемент, движок делает скриншот и спрашивает vision-модель, где
на экране нужный элемент. Координаты проходят через обучение
(skill_stats.json) — повторным LLM-вызовом элемент уже не требует.

Защищённый aios_core/llm_balancer.py НЕ меняется: там нет поддержки
изображений, поэтому провайдеры вызываются напрямую с теми же ключами из
.env / data/.llm_keys.json.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_PROMPT = (
    "You are looking at an Android phone screenshot. Find the UI element described as: \"{hint}\". "
    "If it is visible, respond STRICTLY with JSON: {{\"found\": true, \"x\": <center x>, \"y\": <center y>}} "
    "in image pixels. If it is not visible, respond: {{\"found\": false}}. No extra text."
)


def _png_size(data: bytes) -> tuple[int, int] | None:
    """Размеры PNG из заголовка (без зависимостей); None для других форматов."""
    if len(data) > 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if 0 < width <= 8000 and 0 < height <= 8000:
            return width, height
    return None


def _extract_json(text: str) -> dict | None:
    """Первый сбалансированный JSON-объект из ответа модели."""
    start = str(text or "").find("{")
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(text[start:index + 1])
                    return data if isinstance(data, dict) else None
                except ValueError:
                    return None
    return None


def _runtime_keys() -> dict[str, list[str]]:
    """Ключи провайдеров: env, затем data/.llm_keys.json (схема llm_balancer)."""
    keys: dict[str, list[str]] = {"gemini": [], "openrouter": []}
    for env_key, provider in (("GEMINI_API_KEY", "gemini"), ("OPENROUTER_API_KEY", "openrouter")):
        for index in range(1, 10):
            value = os.environ.get(f"{env_key}_{index}", "")
            if value and value not in keys[provider]:
                keys[provider].append(value)
        base = os.environ.get(env_key, "")
        if base and base not in keys[provider]:
            keys[provider].append(base)
    try:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name == "GEMINI_API_KEY" or name.startswith("GEMINI_API_KEY_"):
                provider = "gemini"
            elif name == "OPENROUTER_API_KEY" or name.startswith("OPENROUTER_API_KEY_"):
                provider = "openrouter"
            else:
                continue
            if value and value not in keys[provider]:
                keys[provider].append(value)
    except OSError:
        pass
    try:
        path = Path(__file__).resolve().parents[2] / "data" / ".llm_keys.json"
        runtime = json.loads(path.read_text(encoding="utf-8"))
        for provider in keys:
            for value in runtime.get(provider) or []:
                if value and value not in keys[provider]:
                    keys[provider].append(str(value))
    except Exception:
        pass
    return keys


class VisionLocator:
    """Находит элемент на скриншоте по текстовому описанию."""

    def __init__(self, *, gemini_model: str = "gemini-2.0-flash",
                 openrouter_model: str = "google/gemini-2.0-flash-001",
                 max_width: int = 720, timeout: int = 60, enabled: bool = True,
                 providers: list[tuple[str, Any, str]] | None = None):
        self.gemini_model = gemini_model
        self.openrouter_model = openrouter_model
        self.max_width = max(240, int(max_width))
        self.timeout = timeout
        self.enabled = enabled
        # providers: [(имя, ask_fn(key, b64, hint) -> dict|None, ключ)] — в тестах подменяется
        self._providers_override = providers

    # ----------------------------------------------------------- helpers

    def _downscale(self, image_path: Path) -> tuple[bytes, float]:
        """Ужимает изображение (масштаб возврата). Без cv2 — отдаёт как есть."""
        raw = Path(image_path).read_bytes()
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            buffer = np.frombuffer(raw, dtype=np.uint8)
            image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if image is None:
                return raw, 1.0
            height, width = image.shape[:2]
            if width <= self.max_width:
                return raw, 1.0
            scale = self.max_width / float(width)
            resized = cv2.resize(image, (self.max_width, int(height * scale)),
                                 interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 82])
            if not ok:
                return raw, 1.0
            return encoded.tobytes(), 1.0 / scale
        except Exception:
            return raw, 1.0

    def _post_json(self, url: str, payload: dict, headers: dict) -> dict:
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _ask_gemini(self, key: str, image_b64: str, hint: str) -> dict | None:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.gemini_model}:generateContent?key={key}")
        payload = {"contents": [{"parts": [
            {"text": _PROMPT.format(hint=hint)},
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}]}]}
        try:
            data = self._post_json(url, payload, {})
            text = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [{}]
            return _extract_json(str(text[0].get("text") or ""))
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def _ask_openrouter(self, key: str, image_b64: str, hint: str) -> dict | None:
        # max_tokens обязателен: без него OpenRouter резервирует весь контекст
        # модели и отвечает 402 на аккаунтах с небольшим балансом.
        payload = {"model": self.openrouter_model, "max_tokens": 60,
                   "messages": [{"role": "user", "content": [
            {"type": "text", "text": _PROMPT.format(hint=hint)},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}]}
        try:
            data = self._post_json("https://openrouter.ai/api/v1/chat/completions", payload,
                                   {"Authorization": f"Bearer {key}"})
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if isinstance(text, list):  # некоторые модели отдают список частей
                text = " ".join(str(part.get("text") or "") for part in text if isinstance(part, dict))
            return _extract_json(str(text))
        except (urllib.error.URLError, OSError, ValueError):
            return None

    # ------------------------------------------------------------ public

    def locate(self, image_path: Path | str, hint: str) -> dict:
        """{"status":"ok","x","y","provider"} или {"status":"error",...}."""
        if not self.enabled:
            return {"status": "error", "error": "vision отключён в конфиге"}
        hint = str(hint or "").strip()
        if not hint:
            return {"status": "error", "error": "пустое описание элемента"}
        try:
            image_bytes, scale = self._downscale(Path(image_path))
        except OSError as exc:
            return {"status": "error", "error": f"screenshot: {exc}"[:160]}
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        frame_size = _png_size(image_bytes)  # реальные размеры кадра (если PNG)
        if self._providers_override is not None:
            providers = self._providers_override
        else:
            keys = _runtime_keys()
            providers = ([("gemini", self._ask_gemini, key) for key in keys["gemini"]]
                         + [("openrouter", self._ask_openrouter, key) for key in keys["openrouter"]])
        for provider, ask, key in providers:
            answer = ask(key, image_b64, hint)
            if not answer:
                continue
            if answer.get("found") is True:
                try:
                    x, y = int(answer["x"]), int(answer["y"])
                except (KeyError, TypeError, ValueError):
                    continue
                if frame_size is not None:
                    max_x, max_y = frame_size[0] / scale, frame_size[1] / scale
                else:
                    max_x, max_y = 4000 * scale, 8000 * scale
                if x < 0 or y < 0 or x > max_x or y > max_y:
                    continue
                return {"status": "ok", "x": int(x * scale), "y": int(y * scale), "provider": provider}
            return {"status": "error", "error": "элемент не виден на экране", "provider": provider}
        return {"status": "error", "error": "vision-провайдеры недоступны"}
