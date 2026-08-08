"""Тесты каталога склада в TG (пагинация, карточки) — tg_bot/catalog.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from tg_bot import catalog


def _mk(name, price, sku):
    return {"name": name, "price": price, "qty": 1, "category": "двигатель",
            "compatibility": "ВАЗ", "location": "Стеллаж", "sku": sku,
            "condition": "used", "photos": [], "reserved_qty": 0}


@pytest.fixture
def inv(tmp_path, monkeypatch):
    """Временный inventory.json с 12 позициями (для пагинации)."""
    # реальное фото для карточки
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0fakejpegdata")
    data = [_mk(f"Деталь {i}", 100 + i * 50, f"AIOS-{i:03d}") for i in range(1, 13)]
    data[0] = {"name": "Маховик двигателя", "price": 1100.0, "qty": 2, "category": "двигатель",
               "compatibility": "ВАЗ 2108-15", "location": "Стеллаж 1", "sku": "AIOS-101",
               "condition": "used", "description": "Совместимость: ВАЗ. Место: Стеллаж 1.",
               "photos": [str(tmp_path / "photo.jpg")], "reserved_qty": 0}
    data[1] = {"name": "Помпа водяная", "price": 350.0, "qty": 5, "category": "система_охлаждения",
               "compatibility": "ВАЗ 2108/2110", "location": "Стеллаж 2", "sku": "AIOS-102",
               "condition": "used", "photos": ["/tmp/nonexist2.jpg"], "reserved_qty": 0}
    data[2] = {"name": "Фара передняя ВАЗ 2105", "price": 600.0, "qty": 1, "category": "оптика",
               "compatibility": "ВАЗ 2105/07", "sku": "AIOS-103", "condition": "used",
               "photos": [], "reserved_qty": 0}
    f = tmp_path / "inventory.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(catalog, "DATA", f)
    return data


class FakeAPI:
    def __init__(self):
        self.messages = []
        self.photos = []

    def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        self.messages.append((text, reply_markup))

    def send_photo(self, chat_id, photo_path, caption="", **kw):
        self.photos.append((photo_path, caption))


def test_catalog_intent_triggers(inv):
    api = FakeAPI()
    assert catalog._handle_catalog_intent(api, 1, "что на складе") is True
    assert any("Позиций" in t for t, _ in api.messages)
    api2 = FakeAPI()
    assert catalog._handle_catalog_intent(api2, 1, "привет") is False


def test_items_page_pagination(inv):
    api = FakeAPI()
    catalog._send_items_page(api, 1, 0)
    text, kb = api.messages[0]
    assert "Товары склада" in text
    assert "Маховик" in text
    # кнопки пагинации
    rows = kb["inline_keyboard"]
    assert any("➡️" in b.get("text", "") for row in rows for b in row)


def test_item_card_photo(inv):
    api = FakeAPI()
    catalog._send_item_card(api, 1, "Маховик")
    assert api.photos  # отправили фото (или fallback сообщение)
    if api.photos:
        caption = api.photos[0][1]
        assert "1100" in caption


def test_item_card_fallback(inv):
    api = FakeAPI()
    catalog._send_item_card(api, 1, "Фара передняя ВАЗ 2105")
    # нет фото -> текстом
    assert any("Фара передняя" in t for t, _ in api.messages)


def test_item_card_not_found(inv):
    api = FakeAPI()
    catalog._send_item_card(api, 1, "несуществующая деталь")
    assert any("не найден" in t for t, _ in api.messages)


def test_item_card_intent_skips_add(inv):
    """«добавь деталь …» не перехватывается карточкой."""
    api = FakeAPI()
    assert catalog._handle_item_card_intent(api, 1, "добавь деталь фара, 2 шт") is False
    assert not api.messages


def test_competitors_intent_no_data(inv, monkeypatch, tmp_path):
    api = FakeAPI()
    # нет файла мониторинга
    monkeypatch.setattr(catalog, "ROOT", tmp_path)
    assert catalog._handle_competitors_intent(api, 1, "конкуренты") is True
    assert any("Нет данных" in t for t, _ in api.messages)
