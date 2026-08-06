"""Telegram route workflow keeps address entry and route selection separate."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class FakeUklon:
    title = "Uklon Passenger"

    def __init__(self):
        self.entered = []
        self.staged = []

    def stage_route(self, pickup, destination, confirm=False, stops=None):
        assert confirm is True
        self.staged.append((pickup, destination, list(stops or [])))
        return {
            "status": "route_staged", "route_id": "route-1",
            "controls": {"pickup_address": True, "destination_address": True},
        }

    def prepare_address_query(self, route_id, field, confirm=False):
        self.entered.append((route_id, field, confirm))
        return {"status": "query_entered"}


def test_uklon_route_requires_second_confirmation_for_text_entry(monkeypatch):
    import run_telegram_bot as bot

    fake = FakeUklon()
    monkeypatch.setattr(bot, "_phone_adapter", lambda key: fake)
    api = API()
    chat_id = 800001
    try:
        assert bot._confirm_phone_pending(api, chat_id, "uklon_stage_route", {
            "pickup": "A", "destination": "B",
        })
        pending = bot._pending_confirm[chat_id]
        assert pending["kind"] == "uklon_enter_route_query"
        assert fake.entered == []
        # The second approval is the only point at which a query can be typed.
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert fake.entered == [("route-1", "pickup", True)]
        assert bot._phone_route_drafts[chat_id]["next_field"] == "destination"
    finally:
        bot._pending_confirm.pop(chat_id, None)
        bot._phone_route_drafts.pop(chat_id, None)


def test_uklon_series_route_intent_preserves_ordered_stops(monkeypatch):
    import run_telegram_bot as bot

    fake = FakeUklon()
    monkeypatch.setattr(bot, "_phone_adapter", lambda key: fake)
    api = API()
    chat_id = 800002
    try:
        assert bot._parse_uklon_route_request("маршрут Uklon: Точка А -> Точка Б -> Точка В") == {
            "pickup": "Точка А", "stops": ["Точка Б"], "destination": "Точка В",
        }
        assert bot._handle_android_phone_workflow_intent(api, chat_id, "маршрут Uklon: Точка А -> Точка Б -> Точка В")
        pending = bot._pending_confirm[chat_id]
        assert pending["kind"] == "uklon_stage_route"
        assert pending["data"]["stops"] == ["Точка Б"]
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert fake.staged == [("Точка А", "Точка В", ["Точка Б"])]
        assert bot._phone_route_drafts[chat_id]["next_field"] == "pickup"
    finally:
        bot._pending_confirm.pop(chat_id, None)
        bot._phone_route_drafts.pop(chat_id, None)


def test_uklon_route_without_pickup_uses_current_location():
    import run_telegram_bot as bot

    assert bot._parse_uklon_route_request("маршрут уклон: -> Точка Б -> Точка В") == {
        "pickup": "", "stops": ["Точка Б"], "destination": "Точка В",
    }
