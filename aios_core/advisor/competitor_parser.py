from __future__ import annotations

import re
import asyncio
import aiohttp
from typing import Any


class CompetitorPriceParser:
    """Парсер для анализа цен конкурентов на OLX/Prom."""

    async def fetch_price(self, session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
        """
        Асинхронно получает страницу по URL и извлекает цену.

        Args:
            session: aiohttp ClientSession для выполнения запроса.
            url: URL страницы для парсинга.

        Returns:
            Словарь с ключами 'url', 'price', 'source' и опционально 'error'.
        """
        try:
            async with session.get(url) as response:
                text = await response.text()
                price = self.extract_price(text)
                if price is not None:
                    return {"url": url, "price": price, "source": "olx"}
                # Если цена не найдена в тексте, пытаемся извлечь из URL
                match = re.search(r"(\d{4,})", url)
                if match:
                    return {"url": url, "price": float(match.group(1)), "source": "olx"}
                return {"url": url, "price": 0.0, "source": "olx", "error": "price_not_found"}
        except Exception as exc:
            return {"url": url, "price": 0.0, "source": "olx", "error": f"request_failed: {exc}"}

    async def parse_olx_links(self, urls: list[str]) -> list[dict[str, Any]]:
        """
        Асинхронно извлекает цены из списка ссылок OLX.

        Args:
            urls: Список URL для парсинга.

        Returns:
            Список словарей с информацией о цене и статусе.
        """
        prices = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_price(session, url) for url in urls]
            prices = await asyncio.gather(*tasks)
        return prices

    @staticmethod
    def extract_price(text: str) -> float | None:
        """
        Извлекает цену из текста страницы.

        Args:
            text: HTML или текст страницы.

        Returns:
            Цена в виде float или None, если не найдена.
        """
        # Пример простого извлечения цены из текста (можно расширить)
        match = re.search(r"(\d{1,3}(?:[ \.,]\d{3})*(?:[.,]\d{2})?)\s*(?:грн|uah|uah\.)", text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(" ", "").replace(",", ".").replace(".", "", match.group(1).count(".") - 1)
            try:
                return float(price_str)
            except ValueError:
                return None
        return None

    def calculate_market_position(self, my_price: float, competitor_prices: list[float]) -> dict[str, Any]:
        """
        Определяет позицию цены на рынке.

        Args:
            my_price: Моя цена.
            competitor_prices: Список цен конкурентов.

        Returns:
            Словарь с позицией и рекомендованным действием.
        """
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