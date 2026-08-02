from __future__ import annotations

import re
import requests


class CompetitorPriceParser:
    """Парсер для анализа цен конкурентов на OLX/Prom."""

    async def parse_olx_links(self, urls: list[str]) -> list[dict[str, float]]:
        """Извлекает цены из списка ссылок OLX (заглушка для реального scraping)."""
        prices = []
        for url in urls:
            # TODO: Реальный HTTP запрос и парсинг BeautifulSoup
            response = requests.get(url)
            price = extract_price(response.text)

            # Имитация: извлекаем число из URL или возвращаем заглушку
            match = re.search(r"(\d{4,})", url)
            if match:
                prices.append({"url": url, "price": float(match.group(1)), "source": "olx"})
            else:
                prices.append({"url": url, "price": 0.0, "source": "olx", "error": "price_not_found"})
        return prices

    def calculate_market_position(self, my_price: float, competitor_prices: list[float]) -> dict[str, object]:
        """Определяет позицию цены на рынке."""
        if not competitor_prices:
            return {"position": "unknown", "recommended_action": "keep_price"}

        avg_price = sum(competitor_prices) / len(competitor_prices)
        min_price = min(competitor_prices)

        if my_price < min_price:
            return {"position": "cheapest", "recommended_action": "increase_slightly"}
        elif my_price <= avg_price * 1.05:
            return {"position": "competitive", "recommended_action": "keep_price"}
        else:
            return {"position": "expensive", "recommended_action": "consider_discount"}


# Refactored function from octopus_core/main.py
import json
import urllib.parse
from typing import Any, Optional
import http.client
import ssl


def gemini_web_reader_hack(
    url: str,
    params: Optional[dict[str, Any]] = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    Безопасно выполняет HTTP POST-запрос к указанному URL с передачей параметров в теле запроса.
    Заменяет небезопасные GET-запросы с параметрами в URL на POST с JSON-телом.

    Args:
        url: URL для запроса.
        params: Словарь параметров для передачи в теле запроса.
        timeout: Таймаут запроса в секундах.

    Returns:
        Распарсенный JSON-ответ в виде словаря.

    Raises:
        ValueError: Если URL некорректен.
        ConnectionError: При ошибках соединения.
        TimeoutError: При превышении таймаута.
        json.JSONDecodeError: Если ответ не является валидным JSON.
    """
    if params is None:
        params = {}

    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")

    host = parsed_url.hostname
    port = parsed_url.port
    path = parsed_url.path or "/"
    if parsed_url.query:
        # Если в URL есть query, добавим их к параметрам
        query_params = urllib.parse.parse_qs(parsed_url.query)
        # parse_qs возвращает значения в списках, преобразуем в простые значения
        for k, v in query_params.items():
            if v:
                params.setdefault(k, v[0])

    if not port:
        port = 443 if parsed_url.scheme == "https" else 80

    body = json.dumps(params).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Accept": "application/json",
        "User-Agent": "gemini-web-reader/1.0",
    }

    try:
        if parsed_url.scheme == "https":
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("POST", path, body=body, headers=headers)
        response = conn.getresponse()
        resp_data = response.read()
        conn.close()

        if response.status != 200:
            raise ConnectionError(f"HTTP error {response.status}: {response.reason}")

        return json.loads(resp_data.decode("utf-8"))

    except (http.client.HTTPException, ConnectionError) as e:
        raise ConnectionError(f"Connection error: {e}") from e
    except ssl.SSLError as e:
        raise ConnectionError(f"SSL error: {e}") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON response: {e.msg}", e.doc, e.pos)
    except TimeoutError as e:
        raise TimeoutError(f"Request timed out: {e}") from e


def extract_price(html_text: str) -> float:
    """
    Заглушка функции для извлечения цены из HTML текста.

    Args:
        html_text: HTML содержимое страницы.

    Returns:
        Извлеченная цена или 0.0 если не найдено.
    """
    # Реализация отсутствует, возвращаем 0.0
    return 0.0