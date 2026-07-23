"""Parametrized tests for OLX AdCard."""

import pytest
from aios_core.modules.olx.cards import AdCard


@pytest.mark.parametrize("title,price,currency,query,expected_title", [
    ("iPhone 12", 15000, "UAH", "iphone", "iPhone 12"),
    ("MacBook Pro", 45000, "UAH", "macbook", "MacBook Pro"),
    ("Samsung TV", 8000, "USD", "tv", "Samsung TV"),
    ("Дитячий візок", 2500, "UAH", "візок", "Дитячий візок"),
])
def test_ad_card_title(title, price, currency, query, expected_title):
    card = AdCard(title=title, price=price, currency=currency, query=query)
    assert card.title == expected_title


@pytest.mark.parametrize("price1,price2,same", [
    (100, 100, True),
    (100, 200, False),
    (None, None, True),
])
def test_ad_card_price_comparison(price1, price2, same):
    c1 = AdCard(title="A", price=price1, currency="UAH", query="q")
    c2 = AdCard(title="A", price=price2, currency="UAH", query="q")
    assert (c1.price == c2.price) == same
