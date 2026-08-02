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

    def calculate_market_position(self, my_price: float, competitor_prices: list[float]) -> dict[str, any]:
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